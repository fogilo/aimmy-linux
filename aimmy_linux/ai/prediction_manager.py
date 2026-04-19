"""
Prediction managers for Aimmy Linux.
Port of AILogic/PredictionManager.cs

Contains three prediction algorithms:
- KalmanPrediction: Kalman filter-based position prediction
- WiseTheFoxPrediction: EMA-based velocity prediction
- ShalloePredictionV2: Historical velocity averaging
"""

import math
import time
from typing import Optional

from utils.config_manager import config


class KalmanPrediction:
    """Kalman filter prediction for smooth target tracking.

    State vector: [x, y, vx, vy]
    Uses a simplified diagonal covariance matrix.
    """

    PROCESS_NOISE = 0.1
    MEASUREMENT_NOISE = 0.5
    MAX_VELOCITY = 5000.0

    def __init__(self):
        self.reset()

    def reset(self):
        self._x = 0.0
        self._y = 0.0
        self._vx = 0.0
        self._vy = 0.0
        self._p00 = 1.0
        self._p11 = 1.0
        self._p22 = 1.0
        self._p33 = 1.0
        self._last_update_time = time.monotonic()
        self._initialized = False

    def update(self, x: int, y: int):
        """Update the filter with a new detection position."""
        now = time.monotonic()

        if not self._initialized:
            self._x = float(x)
            self._y = float(y)
            self._vx = 0.0
            self._vy = 0.0
            self._last_update_time = now
            self._initialized = True
            return

        # Time step, clamped between 1ms and 100ms
        dt = max(0.001, min(0.1, now - self._last_update_time))

        # Prediction step
        predicted_x = self._x + self._vx * dt
        predicted_y = self._y + self._vy * dt

        # Update covariance
        self._p00 += self.PROCESS_NOISE
        self._p11 += self.PROCESS_NOISE
        self._p22 += self.PROCESS_NOISE * 10
        self._p33 += self.PROCESS_NOISE * 10

        # Innovation
        innovation_x = x - predicted_x
        innovation_y = y - predicted_y

        # Kalman gain
        k = self._p00 / (self._p00 + self.MEASUREMENT_NOISE)

        # Update state
        self._x = predicted_x + k * innovation_x
        self._y = predicted_y + k * innovation_y

        # Update velocity
        self._vx += k * innovation_x / dt
        self._vy += k * innovation_y / dt

        # Clamp velocity
        self._vx = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, self._vx))
        self._vy = max(-self.MAX_VELOCITY, min(self.MAX_VELOCITY, self._vy))

        # Update covariance
        self._p00 *= (1 - k)
        self._p11 *= (1 - k)

        self._last_update_time = now

    def get_position(self, mouse_speed: float = 0.0) -> tuple:
        """Get predicted target position.

        Returns:
            (x, y) predicted position as integers
        """
        now = time.monotonic()
        dt = now - self._last_update_time

        current_x = self._x + self._vx * dt
        current_y = self._y + self._vy * dt

        lead_time = float(config.slider_settings.get("Kalman Lead Time", 0.10))

        if mouse_speed > 0.0:
            estimated_completion = 100.0 / mouse_speed
            dynamic_lead = estimated_completion * 0.4
            lead_time = dynamic_lead * (lead_time / 0.10)
            lead_time = max(0.02, min(0.3, lead_time))

        predicted_x = current_x + self._vx * lead_time
        predicted_y = current_y + self._vy * lead_time

        return (int(predicted_x), int(predicted_y))


class WiseTheFoxPrediction:
    """EMA-based prediction with velocity tracking.

    Uses exponential moving average for both position and velocity smoothing.
    """

    ALPHA = 0.5  # Smoothing factor

    def __init__(self):
        self.reset()

    def reset(self):
        self._ema_x = 0.0
        self._ema_y = 0.0
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._prev_x = 0.0
        self._prev_y = 0.0
        self._last_update_time = time.monotonic()
        self._initialized = False

    def update(self, x: int, y: int):
        """Update with a new detection position."""
        now = time.monotonic()

        if not self._initialized:
            self._ema_x = float(x)
            self._ema_y = float(y)
            self._prev_x = float(x)
            self._prev_y = float(y)
            self._velocity_x = 0.0
            self._velocity_y = 0.0
            self._last_update_time = now
            self._initialized = True
            return

        dt = max(0.001, min(0.1, now - self._last_update_time))

        # EMA on position
        self._ema_x = self.ALPHA * x + (1.0 - self.ALPHA) * self._ema_x
        self._ema_y = self.ALPHA * y + (1.0 - self.ALPHA) * self._ema_y

        # Velocity (pixels/second)
        new_vx = (self._ema_x - self._prev_x) / dt
        new_vy = (self._ema_y - self._prev_y) / dt

        # EMA on velocity
        self._velocity_x = self.ALPHA * new_vx + (1.0 - self.ALPHA) * self._velocity_x
        self._velocity_y = self.ALPHA * new_vy + (1.0 - self.ALPHA) * self._velocity_y

        self._prev_x = self._ema_x
        self._prev_y = self._ema_y
        self._last_update_time = now

    def get_position(self) -> tuple:
        """Get estimated/predicted position.

        Returns:
            (x, y) predicted position as integers
        """
        lead_time = float(config.slider_settings.get("WiseTheFox Lead Time", 0.15))

        predicted_x = self._ema_x + self._velocity_x * lead_time
        predicted_y = self._ema_y + self._velocity_y * lead_time

        return (int(predicted_x), int(predicted_y))


class ShalloePredictionV2:
    """Velocity-based prediction using historical velocity averaging.

    Maintains a rolling window of velocity samples and predicts
    future position based on average velocity * lead multiplier.
    """

    MAX_HISTORY = 5

    def __init__(self):
        self.reset()

    def reset(self):
        self._velocity_x_history = []
        self._velocity_y_history = []
        self._prev_x = 0
        self._prev_y = 0
        self._initialized = False

    def update(self, x: int, y: int):
        """Update with new target position."""
        if not self._initialized:
            self._prev_x = x
            self._prev_y = y
            self._initialized = True
            return

        vx = x - self._prev_x
        vy = y - self._prev_y

        if len(self._velocity_x_history) >= self.MAX_HISTORY:
            self._velocity_x_history.pop(0)
            self._velocity_y_history.pop(0)

        self._velocity_x_history.append(vx)
        self._velocity_y_history.append(vy)

        self._prev_x = x
        self._prev_y = y

    def get_position(self) -> tuple:
        """Get predicted position.

        Returns:
            (x, y) predicted position as integers
        """
        if not self._initialized or not self._velocity_x_history:
            return (self._prev_x, self._prev_y)

        lead = float(config.slider_settings.get("Shalloe Lead Multiplier", 3.0))

        avg_vx = sum(self._velocity_x_history) / len(self._velocity_x_history)
        avg_vy = sum(self._velocity_y_history) / len(self._velocity_y_history)

        return (
            int(self._prev_x + avg_vx * lead),
            int(self._prev_y + avg_vy * lead),
        )
