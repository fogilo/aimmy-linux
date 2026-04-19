"""
Core AI manager for Aimmy Linux.
Port of AILogic/AIManager.cs

Manages ONNX model inference, detection processing, sticky aim,
and the main AI loop. Uses ONNX Runtime with CUDA/CPU instead of DirectML.
"""

import json
import math
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ai.capture_manager import CaptureManager
from ai.math_util import (
    Prediction, calculate_num_detections, get_distance_sq,
    image_to_float_chw,
)
from ai.prediction_manager import (
    KalmanPrediction, ShalloePredictionV2, WiseTheFoxPrediction,
)
from input.mouse_manager import mouse_manager
from input.input_binding import input_binding_manager
from utils.config_manager import config
from utils.display_manager import display_manager
from utils.log_manager import LogLevel, log


class AIManager:
    """Core AI engine — runs ONNX inference and drives aim assist."""

    # Sticky aim constants
    LOCK_SCORE_DECAY = 0.85
    LOCK_SCORE_GAIN = 15.0
    MAX_LOCK_SCORE = 100.0
    REFERENCE_TARGET_SIZE = 10000.0
    MAX_FRAMES_WITHOUT_TARGET = 3
    SAVE_FRAME_COOLDOWN = 0.5  # seconds

    def __init__(self, model_path: str):
        self._image_size = int(config.dropdown_state.get("Image Size", "640"))
        self._num_detections = 8400
        self._num_classes = 1
        self._is_dynamic = False
        self._model_classes: Dict[int, str] = {0: "enemy"}

        self._capture = CaptureManager()
        self._capture.initialize()

        self._kalman = KalmanPrediction()
        self._wtf = WiseTheFoxPrediction()
        self._shalloe = ShalloePredictionV2()

        self._session = None
        self._input_name = "images"
        self._output_names = []

        # Sticky aim state
        self._current_target: Optional[Prediction] = None
        self._consecutive_no_target = 0
        self._frames_without_match = 0
        self._last_vel_x = 0.0
        self._last_vel_y = 0.0
        self._lock_score = 0.0

        self._last_detection_box = (0.0, 0.0, 0.0, 0.0)
        self._detected_x = 0
        self._detected_y = 0
        self._ai_conf = 0.0

        # Loop control
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Benchmarking
        self._iter_count = 0
        self._total_time = 0.0
        self._last_save_time = 0.0

        # Initialize model
        self._init_model(model_path)

    def _init_model(self, model_path: str):
        """Load the ONNX model with GPU or CPU provider."""
        try:
            import onnxruntime as ort

            providers = ort.get_available_providers()
            log(LogLevel.INFO, f"Available ONNX providers: {providers}")

            # Try GPU first, fall back to CPU
            if "CUDAExecutionProvider" in providers:
                selected = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                log(LogLevel.INFO, "Using CUDA GPU acceleration")
            elif "ROCMExecutionProvider" in providers:
                selected = ["ROCMExecutionProvider", "CPUExecutionProvider"]
                log(LogLevel.INFO, "Using ROCm GPU acceleration")
            else:
                selected = ["CPUExecutionProvider"]
                log(LogLevel.WARNING, "No GPU provider found, using CPU (may be slow)",
                    notify_user=True)

            opts = ort.SessionOptions()
            opts.enable_cpu_mem_arena = True
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 4

            self._session = ort.InferenceSession(model_path, opts, providers=selected)
            inputs = self._session.get_inputs()
            outputs = self._session.get_outputs()

            self._input_name = inputs[0].name
            self._output_names = [o.name for o in outputs]

            # Detect dynamic vs fixed model
            input_shape = inputs[0].shape
            log(LogLevel.INFO, f"Model input: {self._input_name} shape={input_shape}")
            for o in outputs:
                log(LogLevel.INFO, f"Model output: {o.name} shape={o.shape}")

            is_dynamic = any(isinstance(d, str) or d == -1 or d is None for d in input_shape)
            self._is_dynamic = is_dynamic

            if is_dynamic:
                self._num_detections = calculate_num_detections(self._image_size)
                log(LogLevel.INFO,
                    f"Dynamic model — using {self._image_size}x{self._image_size}, "
                    f"{self._num_detections} detections", notify_user=True)
            else:
                fixed_size = input_shape[2] if len(input_shape) >= 3 else 640
                self._image_size = int(fixed_size)
                self._num_detections = calculate_num_detections(self._image_size)
                config.dropdown_state["Image Size"] = str(self._image_size)
                log(LogLevel.INFO,
                    f"Fixed model — {self._image_size}x{self._image_size}", notify_user=True)

            self._load_classes()
            self._start_loop()

        except Exception as e:
            log(LogLevel.ERROR, f"Failed to load model: {e}", notify_user=True)

    def _load_classes(self):
        """Load class names from model metadata."""
        if self._session is None:
            return
        try:
            meta = self._session.get_modelmeta()
            custom = meta.custom_metadata_map
            if "names" in custom:
                data = json.loads(custom["names"])
                self._model_classes = {}
                for k, v in data.items():
                    self._model_classes[int(k)] = str(v)
                self._num_classes = max(self._model_classes.keys()) + 1 if self._model_classes else 1
                log(LogLevel.INFO, f"Loaded {len(self._model_classes)} class(es): {self._model_classes}")
        except Exception as e:
            log(LogLevel.ERROR, f"Error loading classes: {e}")

    # --- Main AI Loop ---

    def _start_loop(self):
        self._running = True
        self._thread = threading.Thread(target=self._ai_loop, daemon=True)
        self._thread.start()

    def _should_process(self) -> bool:
        return (config.toggle_state.get("Aim Assist", False) or
                config.toggle_state.get("Show Detected Player", False) or
                config.toggle_state.get("Auto Trigger", False))

    def _should_predict(self) -> bool:
        return (config.toggle_state.get("Show Detected Player", False) or
                config.toggle_state.get("Constant AI Tracking", False) or
                input_binding_manager.is_holding("Aim Keybind") or
                input_binding_manager.is_holding("Second Aim Keybind"))

    def _ai_loop(self):
        """Main AI processing loop running on a background thread."""
        while self._running:
            t0 = time.monotonic()

            if self._should_process():
                if self._should_predict():
                    prediction = self._get_closest_prediction()
                    if prediction is not None:
                        self._calculate_coordinates(prediction)
                        self._handle_aim(prediction)
                        elapsed = time.monotonic() - t0
                        self._total_time += elapsed
                        self._iter_count += 1
                    else:
                        time.sleep(0.001)
                else:
                    time.sleep(0.001)
            else:
                time.sleep(0.01)

    # --- Detection Pipeline ---

    def _get_closest_prediction(self) -> Optional[Prediction]:
        """Capture screen, run inference, return best detection."""
        dm = display_manager
        img_size = self._image_size

        # Determine detection center
        if config.dropdown_state.get("Detection Area Type") == "Closest to Mouse":
            mx, my = mouse_manager.cursor_position
            if dm.is_point_in_current_display(mx, my):
                target_x, target_y = mx, my
            else:
                target_x = dm.screen_left + dm.screen_width // 2
                target_y = dm.screen_top + dm.screen_height // 2
        else:
            target_x = dm.screen_left + dm.screen_width // 2
            target_y = dm.screen_top + dm.screen_height // 2

        det_x = target_x - img_size // 2
        det_y = target_y - img_size // 2

        # Screen capture
        frame = self._capture.screen_grab(det_x, det_y, img_size, img_size)
        if frame is None:
            return None

        try:
            # Preprocess: resize + normalize to CHW float32
            input_tensor = image_to_float_chw(frame, img_size)

            # Inference
            results = self._session.run(
                self._output_names,
                {self._input_name: input_tensor},
            )
            output = results[0]  # shape: (1, 4+num_classes, num_detections)

            # Parse detections
            fov_size = float(config.slider_settings.get("FOV Size", 640))
            fov_min = (img_size - fov_size) / 2.0
            fov_max = (img_size + fov_size) / 2.0

            predictions = self._parse_detections(
                output, det_x, det_y, fov_min, fov_max, fov_min, fov_max
            )

            if not predictions:
                return None

            # Find closest to center
            center = img_size / 2.0
            best = None
            best_dist = float('inf')
            for p in predictions:
                dx = p.center_x_translated * img_size - center
                dy = p.center_y_translated * img_size - center
                d2 = dx * dx + dy * dy
                if d2 < best_dist:
                    best_dist = d2
                    best = p

            # Sticky aim
            final = self._handle_sticky_aim(best, predictions)
            if final is not None:
                self._update_detection_box(final, det_x, det_y)
            return final

        except Exception as e:
            log(LogLevel.ERROR, f"Inference error: {e}")
            return None

    def _parse_detections(
        self, output: np.ndarray,
        det_x: int, det_y: int,
        fov_min_x: float, fov_max_x: float,
        fov_min_y: float, fov_max_y: float,
    ) -> List[Prediction]:
        """Parse raw ONNX output into Prediction objects."""
        min_conf = float(config.slider_settings.get("AI Minimum Confidence", 45)) / 100.0
        selected_class = config.dropdown_state.get("Target Class", "Best Confidence")
        selected_id = -1
        if selected_class != "Best Confidence":
            for cid, cname in self._model_classes.items():
                if cname == selected_class:
                    selected_id = cid
                    break

        results = []
        num_det = min(output.shape[2], self._num_detections)

        for i in range(num_det):
            cx = float(output[0, 0, i])
            cy = float(output[0, 1, i])
            w = float(output[0, 2, i])
            h = float(output[0, 3, i])

            best_id = 0
            best_conf = 0.0

            if self._num_classes == 1:
                best_conf = float(output[0, 4, i])
            elif selected_id == -1:
                for c in range(self._num_classes):
                    cc = float(output[0, 4 + c, i])
                    if cc > best_conf:
                        best_conf = cc
                        best_id = c
            else:
                best_conf = float(output[0, 4 + selected_id, i])
                best_id = selected_id

            if best_conf < min_conf:
                continue

            x_min = cx - w / 2
            y_min = cy - h / 2
            x_max = cx + w / 2
            y_max = cy + h / 2

            if x_min < fov_min_x or x_max > fov_max_x:
                continue
            if y_min < fov_min_y or y_max > fov_max_y:
                continue

            results.append(Prediction(
                rect_x=x_min, rect_y=y_min, rect_w=w, rect_h=h,
                confidence=best_conf, class_id=best_id,
                class_name=self._model_classes.get(best_id, f"Class_{best_id}"),
                center_x_translated=cx / self._image_size,
                center_y_translated=cy / self._image_size,
                screen_center_x=det_x + cx,
                screen_center_y=det_y + cy,
            ))

        return results

    # --- Sticky Aim ---

    def _handle_sticky_aim(self, best: Optional[Prediction],
                           predictions: List[Prediction]) -> Optional[Prediction]:
        if not config.toggle_state.get("Sticky Aim", False):
            self._current_target = best
            self._reset_sticky()
            return best

        if best is None or not predictions:
            return self._handle_no_detections()

        self._consecutive_no_target = 0
        img_center = self._image_size / 2.0

        # Find what user is aiming at
        aim_target = None
        nearest_dist = float('inf')
        for p in predictions:
            d = get_distance_sq(p.screen_center_x, p.screen_center_y,
                                img_center, img_center)
            if d < nearest_dist:
                nearest_dist = d
                aim_target = p

        if aim_target is None:
            return self._handle_no_detections()

        if self._current_target is None:
            return self._acquire_target(aim_target)

        # Check if aim target is same as current
        last_x = self._current_target.screen_center_x
        last_y = self._current_target.screen_center_y
        area = self._current_target.rect_w * self._current_target.rect_h
        size = math.sqrt(max(area, 1))
        tracking_r = size * 3.0

        aim_dist = get_distance_sq(aim_target.screen_center_x,
                                    aim_target.screen_center_y, last_x, last_y)
        aim_area = aim_target.rect_w * aim_target.rect_h
        size_ratio = min(area, aim_area) / max(area, aim_area) if max(area, aim_area) > 0 else 0

        is_same = aim_dist < (tracking_r * tracking_r) and size_ratio > 0.5

        if is_same:
            self._frames_without_match = 0
            self._lock_score = min(self.MAX_LOCK_SCORE, self._lock_score + self.LOCK_SCORE_GAIN)
            self._update_velocity(aim_target)
            self._current_target = aim_target
            return aim_target

        self._frames_without_match += 1
        threshold = float(config.slider_settings.get("Sticky Aim Threshold", 50))
        very_centered = nearest_dist < (threshold * threshold * 0.25)

        if very_centered or self._frames_without_match >= 3:
            return self._acquire_target(aim_target)

        return None

    def _handle_no_detections(self) -> Optional[Prediction]:
        if self._current_target is not None:
            self._consecutive_no_target += 1
            if self._consecutive_no_target <= self.MAX_FRAMES_WITHOUT_TARGET:
                self._lock_score *= self.LOCK_SCORE_DECAY
                return Prediction(
                    rect_x=self._current_target.rect_x,
                    rect_y=self._current_target.rect_y,
                    rect_w=self._current_target.rect_w,
                    rect_h=self._current_target.rect_h,
                    confidence=self._current_target.confidence * (1 - self._consecutive_no_target * 0.2),
                    class_id=self._current_target.class_id,
                    class_name=self._current_target.class_name,
                    screen_center_x=self._current_target.screen_center_x + self._last_vel_x * self._consecutive_no_target,
                    screen_center_y=self._current_target.screen_center_y + self._last_vel_y * self._consecutive_no_target,
                    center_x_translated=self._current_target.center_x_translated,
                    center_y_translated=self._current_target.center_y_translated,
                )
        self._reset_sticky()
        return None

    def _acquire_target(self, target: Prediction) -> Prediction:
        self._last_vel_x = 0.0
        self._last_vel_y = 0.0
        self._lock_score = self.LOCK_SCORE_GAIN
        self._frames_without_match = 0
        self._current_target = target
        return target

    def _update_velocity(self, new_target: Prediction):
        if self._current_target:
            vx = new_target.screen_center_x - self._current_target.screen_center_x
            vy = new_target.screen_center_y - self._current_target.screen_center_y
            self._last_vel_x = self._last_vel_x * 0.7 + vx * 0.3
            self._last_vel_y = self._last_vel_y * 0.7 + vy * 0.3

    def _reset_sticky(self):
        self._current_target = None
        self._consecutive_no_target = 0
        self._frames_without_match = 0
        self._last_vel_x = 0.0
        self._last_vel_y = 0.0
        self._lock_score = 0.0

    # --- Aim Handling ---

    def _calculate_coordinates(self, prediction: Prediction):
        self._ai_conf = prediction.confidence
        scale_x = display_manager.screen_width / float(self._image_size)
        scale_y = display_manager.screen_height / float(self._image_size)

        y_offset = float(config.slider_settings.get("Y Offset (Up/Down)", 0))
        x_offset = float(config.slider_settings.get("X Offset (Left/Right)", 0))

        if config.toggle_state.get("X Axis Percentage Adjustment", False):
            pct = float(config.slider_settings.get("X Offset (%)", 50))
            self._detected_x = int((prediction.rect_x + prediction.rect_w * (pct / 100)) * scale_x)
        else:
            self._detected_x = int((prediction.rect_x + prediction.rect_w / 2) * scale_x + x_offset)

        if config.toggle_state.get("Y Axis Percentage Adjustment", False):
            pct = float(config.slider_settings.get("Y Offset (%)", 50))
            self._detected_y = int((prediction.rect_y + prediction.rect_h - prediction.rect_h * (pct / 100)) * scale_y + y_offset)
        else:
            alignment = config.dropdown_state.get("Aiming Boundaries Alignment", "Center")
            y_base = prediction.rect_y
            if alignment == "Center":
                y_base += prediction.rect_h / 2
            elif alignment == "Bottom":
                y_base += prediction.rect_h
            self._detected_y = int(y_base * scale_y + y_offset)

    def _handle_aim(self, prediction: Prediction):
        if not config.toggle_state.get("Aim Assist", False):
            return
        if not (config.toggle_state.get("Constant AI Tracking", False) or
                input_binding_manager.is_holding("Aim Keybind") or
                input_binding_manager.is_holding("Second Aim Keybind")):
            return

        if config.toggle_state.get("Predictions", False):
            method = config.dropdown_state.get("Prediction Method", "Kalman Filter")
            if method == "Kalman Filter":
                self._kalman.update(self._detected_x, self._detected_y)
                px, py = self._kalman.get_position()
                mouse_manager.move_crosshair(px, py)
            elif method == "Shall0e's Prediction":
                self._shalloe.update(self._detected_x, self._detected_y)
                px, py = self._shalloe.get_position()
                mouse_manager.move_crosshair(px, py)
            elif method == "wisethef0x's EMA Prediction":
                self._wtf.update(self._detected_x, self._detected_y)
                px, py = self._wtf.get_position()
                mouse_manager.move_crosshair(px, py)
        else:
            mouse_manager.move_crosshair(self._detected_x, self._detected_y)

    def _update_detection_box(self, target: Prediction, det_x: int, det_y: int):
        self._last_detection_box = (
            target.rect_x + det_x, target.rect_y + det_y,
            target.rect_w, target.rect_h,
        )

    # --- Lifecycle ---

    def get_fps(self) -> float:
        if self._iter_count > 0 and self._total_time > 0:
            return self._iter_count / self._total_time
        return 0.0

    def dispose(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        fps = self.get_fps()
        if fps > 0:
            log(LogLevel.INFO, f"AI Manager shutting down. Average FPS: {fps:.1f}")

        self._capture.dispose()
        if self._session:
            del self._session
            self._session = None
