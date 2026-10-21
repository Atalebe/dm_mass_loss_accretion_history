"""Historical OLS function; extracted without module-level acquisition code."""
import math
import numpy as np

def ols(y: np.ndarray, X: np.ndarray) -> dict:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    resid = y - pred

    n = int(len(y))
    k = int(X.shape[1])
    rss = float(np.sum(resid ** 2))
    tss = float(np.sum((y - y.mean()) ** 2))
    sigma2 = rss / max(n, 1)

    bic = n * math.log(max(sigma2, 1e-300)) + k * math.log(max(n, 2))
    aic = n * math.log(max(sigma2, 1e-300)) + 2 * k
    r2 = 0.0 if tss <= 0 else max(0.0, min(1.0, 1.0 - rss / tss))

    dof = max(n - k, 1)
    sigma2_unbiased = rss / dof
    xtx_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(xtx_inv) * sigma2_unbiased, 0.0))
    t = np.divide(beta, se, out=np.full_like(beta, np.nan), where=se > 0)

    return {
        "beta": beta,
        "se": se,
        "t": t,
        "rss": rss,
        "bic": float(bic),
        "aic": float(aic),
        "r2": float(r2),
        "n": n,
        "k": k,
    }
