"""ml_metrics helpers."""
import numpy as np
from app.services.ml_metrics import mae, mape, pinball_loss, rmse, smape


def test_metrics_shapes():
    y = np.array([1.0, 2.0, 3.0])
    p = np.array([1.1, 2.2, 2.7])
    assert mae(y, p) >= 0
    assert rmse(y, p) >= 0
    assert mape(y, p) >= 0
    assert smape(y, p) >= 0
    assert pinball_loss(y, p, 0.5) >= 0
