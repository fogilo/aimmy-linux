#!/usr/bin/env python3
"""
Aimmy Linux — AI Aim Alignment Tool (Linux Port)
Main entry point for both CLI and GUI modes.

Usage:
    python main.py                          # Start with GUI (Phase 2)
    python main.py --cli --model path.onnx  # CLI mode (Phase 1)
    python main.py --test                   # Run basic self-tests
"""

import argparse
import os
import signal
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.log_manager import setup_logging, log, LogLevel
from utils.config_manager import config, ensure_directories, load_config, save_config
from utils.display_manager import display_manager


def run_cli(model_path: str):
    """Run the AI engine in CLI mode (no GUI)."""
    from ai.ai_manager import AIManager
    from input.input_binding import input_binding_manager

    log(LogLevel.INFO, "=" * 60)
    log(LogLevel.INFO, "Aimmy Linux — CLI Mode")
    log(LogLevel.INFO, "=" * 60)

    # Initialize display manager
    display_manager.initialize()
    displays = display_manager.get_all_displays()
    log(LogLevel.INFO, f"Detected {len(displays)} display(s):")
    for d in displays:
        log(LogLevel.INFO, f"  [{d.index}] {d.device_name}: "
            f"{d.width}x{d.height} at ({d.x},{d.y})"
            f"{' (primary)' if d.is_primary else ''}")
    log(LogLevel.INFO, f"Active display: [{display_manager.current_display_index}]")

    # Setup keybindings
    for binding_id, key_code in config.binding_settings.items():
        input_binding_manager.setup_default(binding_id, key_code)
    log(LogLevel.INFO, f"Keybindings loaded: {config.binding_settings}")

    # Enable aim assist
    config.toggle_state["Aim Assist"] = True
    log(LogLevel.INFO, "Aim Assist ENABLED")
    log(LogLevel.INFO, f"FOV Size: {config.slider_settings['FOV Size']}")
    log(LogLevel.INFO, f"Sensitivity: {config.slider_settings['Mouse Sensitivity (+/-)']}")
    log(LogLevel.INFO, f"Movement Path: {config.dropdown_state['Movement Path']}")

    # Load AI model
    log(LogLevel.INFO, f"Loading model: {model_path}")
    ai_manager = AIManager(model_path)

    log(LogLevel.INFO, "")
    log(LogLevel.INFO, "Aim assist is running. Press Ctrl+C to stop.")
    log(LogLevel.INFO, f"Hold '{config.binding_settings['Aim Keybind']}' to aim.")

    # Keep running until interrupted
    def signal_handler(sig, frame):
        log(LogLevel.INFO, "\nShutting down...")
        ai_manager.dispose()
        input_binding_manager.stop_listening()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Print FPS periodically
    try:
        while True:
            time.sleep(5.0)
            fps = ai_manager.get_fps()
            if fps > 0:
                log(LogLevel.INFO, f"AI FPS: {fps:.1f}")
    except KeyboardInterrupt:
        signal_handler(None, None)


def run_tests():
    """Run basic self-tests to verify all modules load correctly."""
    log(LogLevel.INFO, "=" * 60)
    log(LogLevel.INFO, "Aimmy Linux — Self Test")
    log(LogLevel.INFO, "=" * 60)
    passed = 0
    failed = 0

    # Test 1: Config manager
    try:
        assert config.toggle_state["Aim Assist"] is False
        assert config.slider_settings["FOV Size"] == 640
        log(LogLevel.INFO, "[PASS] Config manager")
        passed += 1
    except Exception as e:
        log(LogLevel.ERROR, f"[FAIL] Config manager: {e}")
        failed += 1

    # Test 2: Display manager
    try:
        display_manager.initialize()
        assert display_manager.screen_width > 0
        assert display_manager.screen_height > 0
        log(LogLevel.INFO, f"[PASS] Display manager: {display_manager.screen_width}x{display_manager.screen_height}")
        passed += 1
    except Exception as e:
        log(LogLevel.ERROR, f"[FAIL] Display manager: {e}")
        failed += 1

    # Test 3: Screen capture
    try:
        from ai.capture_manager import CaptureManager
        cap = CaptureManager()
        cap.initialize()
        frame = cap.screen_grab(0, 0, 320, 320)
        assert frame is not None
        assert frame.shape == (320, 320, 3)
        log(LogLevel.INFO, f"[PASS] Screen capture: shape={frame.shape}, dtype={frame.dtype}")
        cap.dispose()
        passed += 1
    except Exception as e:
        log(LogLevel.ERROR, f"[FAIL] Screen capture: {e}")
        failed += 1

    # Test 4: Math utilities
    try:
        from ai.math_util import calculate_num_detections, image_to_float_chw
        import numpy as np
        assert calculate_num_detections(640) == 8400
        assert calculate_num_detections(320) == 2100
        dummy = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        tensor = image_to_float_chw(dummy, 640)
        assert tensor.shape == (1, 3, 640, 640)
        assert tensor.dtype == np.float32
        log(LogLevel.INFO, "[PASS] Math utilities")
        passed += 1
    except Exception as e:
        log(LogLevel.ERROR, f"[FAIL] Math utilities: {e}")
        failed += 1

    # Test 5: Prediction managers
    try:
        from ai.prediction_manager import KalmanPrediction, WiseTheFoxPrediction, ShalloePredictionV2
        kp = KalmanPrediction()
        kp.update(100, 100)
        kp.update(110, 105)
        pos = kp.get_position()
        assert len(pos) == 2

        wtf = WiseTheFoxPrediction()
        wtf.update(100, 100)
        wtf.update(110, 105)
        pos = wtf.get_position()
        assert len(pos) == 2

        sp = ShalloePredictionV2()
        sp.update(100, 100)
        sp.update(110, 105)
        pos = sp.get_position()
        assert len(pos) == 2
        log(LogLevel.INFO, "[PASS] Prediction managers")
        passed += 1
    except Exception as e:
        log(LogLevel.ERROR, f"[FAIL] Prediction managers: {e}")
        failed += 1

    # Test 6: Movement paths
    try:
        from input.movement_paths import cubic_bezier, lerp, exponential, adaptive, perlin_noise
        p = lerp((0, 0), (100, 100), 0.5)
        assert p == (50, 50)
        p = cubic_bezier((0, 0), (100, 100), (30, 0), (70, 100), 0.5)
        assert len(p) == 2
        log(LogLevel.INFO, "[PASS] Movement paths")
        passed += 1
    except Exception as e:
        log(LogLevel.ERROR, f"[FAIL] Movement paths: {e}")
        failed += 1

    # Test 7: ONNX Runtime
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        gpu = "CUDAExecutionProvider" in providers or "ROCMExecutionProvider" in providers
        log(LogLevel.INFO, f"[PASS] ONNX Runtime: providers={providers}, GPU={'yes' if gpu else 'no'}")
        passed += 1
    except ImportError:
        log(LogLevel.ERROR, "[FAIL] ONNX Runtime: not installed. Run: pip install onnxruntime-gpu")
        failed += 1

    # Test 8: pynput
    try:
        from pynput.mouse import Controller
        c = Controller()
        pos = c.position
        log(LogLevel.INFO, f"[PASS] pynput: cursor at {pos}")
        passed += 1
    except Exception as e:
        log(LogLevel.ERROR, f"[FAIL] pynput: {e}")
        failed += 1

    log(LogLevel.INFO, "")
    log(LogLevel.INFO, f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Aimmy Linux — AI Aim Alignment Tool")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no GUI)")
    parser.add_argument("--model", type=str, help="Path to ONNX model file")
    parser.add_argument("--test", action="store_true", help="Run self-tests")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=str, help="Path to config file to load")
    args = parser.parse_args()

    setup_logging(debug=args.debug)
    ensure_directories()

    if args.config:
        load_config(config.slider_settings, args.config)
        load_config(config.toggle_state, args.config, strict=False)

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    if args.cli:
        if not args.model:
            # Check for models in bin/models
            model_dir = config.get_bin_dir() / "models"
            models = list(model_dir.glob("*.onnx")) if model_dir.exists() else []
            if models:
                model_path = str(models[0])
                log(LogLevel.INFO, f"Auto-selected model: {model_path}")
            else:
                log(LogLevel.ERROR, "No model specified. Use --model <path.onnx> or place .onnx files in bin/models/")
                sys.exit(1)
        else:
            model_path = args.model

        run_cli(model_path)
    else:
        # GUI mode (Phase 2)
        try:
            from ui.main_window import run_gui
            run_gui()
        except ImportError:
            log(LogLevel.WARNING, "GUI not yet implemented. Use --cli mode or --test.")
            log(LogLevel.INFO, "Usage: python main.py --cli --model path/to/model.onnx")
            log(LogLevel.INFO, "       python main.py --test")
            sys.exit(1)


if __name__ == "__main__":
    main()
