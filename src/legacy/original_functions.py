"""Numerical functions extracted without module-level I/O; original statement bodies unchanged."""
import math
import numpy as np
import pandas as pd

FORMATION_CONTROLS = ["a10", "a25", "a50", "a75"]

VMAX_CANDIDATES = [
    "present_vmax_tree",
    "present_vmax",
    "vmax_tree",
    "vmax",
    "SubhaloVmax",
    "subhalo_vmax",
    "Vmax",
]

LOG_MASS_CANDIDATES = [
    "present_log_mass",
    "log_present_mass",
    "log_mass",
    "present_log_mvir",
    "log_mvir",
    "log_m200c",
]

MASS_LINEAR_CANDIDATES = [
    "present_mvir_tree",
    "present_mass_tree",
    "present_mass",
    "mvir",
    "mass",
    "Mvir",
]

ACC_CANDIDATES = [
    "present_acc_rate",
    "present_accretion_rate",
    "acc_rate",
    "accretion_rate",
    "present_specific_acc_rate",
]

MASS_BIN_CANDIDATES = [
    "mass_bin",
    "mass_bin_id",
    "present_mass_bin",
    "mass_stratum",
    "mass_decile",
    "mass_quartile",
]

def canonical_id(value) -> str:
    text = str(value).strip()
    try:
        number = float(text)
        if math.isfinite(number) and number.is_integer():
            return str(int(number))
    except Exception:
        pass
    return text

def gamma_col(gamma: float) -> str:
    return "M_acc_gamma_" + str(gamma).replace(".", "p")

def log10_positive(values: pd.Series) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    return np.log10(x.where(x > 0))

def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    lowered = {c.lower(): c for c in df.columns}
    for col in candidates:
        if col.lower() in lowered:
            return lowered[col.lower()]
    return None

def resolve_feature_id(features: pd.DataFrame) -> str:
    for candidate in [
        "tree_root_id",
        "root_id",
        "tree_id",
        "physical_subhalo_id",
        "subhalo_id",
        "halo_id",
    ]:
        if candidate in features.columns:
            return candidate

    for column in features.columns:
        lowered = column.lower()
        if "root" in lowered and "id" in lowered:
            return column

    raise KeyError(f"could not resolve feature ID; columns={features.columns.tolist()}")

def standardize(values: pd.Series) -> pd.Series:
    x = pd.to_numeric(values, errors="coerce")
    sd = float(x.std(ddof=0))
    if not np.isfinite(sd) or sd <= 0:
        return pd.Series(np.nan, index=x.index)
    return (x - float(x.mean())) / sd

def add_yv_and_base_columns(df: pd.DataFrame, branch_id: str, n_mass_bins: int) -> tuple[pd.DataFrame, dict, list[str]]:
    work = df.copy()

    vmax_col = first_existing(work, VMAX_CANDIDATES)
    if vmax_col is None:
        raise KeyError(f"{branch_id}: no Vmax column found")

    log_mass_col = first_existing(work, LOG_MASS_CANDIDATES)
    if log_mass_col is None:
        mass_col = first_existing(work, MASS_LINEAR_CANDIDATES)
        if mass_col is None:
            raise KeyError(f"{branch_id}: no mass or log-mass column found")
        work["present_log_mass"] = log10_positive(work[mass_col])
        log_mass_col = "present_log_mass"
    elif log_mass_col != "present_log_mass":
        work["present_log_mass"] = pd.to_numeric(work[log_mass_col], errors="coerce")
        log_mass_col = "present_log_mass"
    else:
        work["present_log_mass"] = pd.to_numeric(work["present_log_mass"], errors="coerce")

    acc_col = first_existing(work, ACC_CANDIDATES)
    if acc_col is None:
        raise KeyError(f"{branch_id}: no present accretion-rate column found")
    if acc_col != "present_acc_rate":
        work["present_acc_rate"] = pd.to_numeric(work[acc_col], errors="coerce")
    else:
        work["present_acc_rate"] = pd.to_numeric(work["present_acc_rate"], errors="coerce")

    work["target_yv_log_vmax_mass_scaled"] = (
        log10_positive(work[vmax_col]) - (1.0 / 3.0) * work["present_log_mass"]
    )

    m = work["present_log_mass"]
    m_z = (m - float(m.mean())) / float(m.std(ddof=0))
    work["mass_z"] = m_z
    work["mass_z2"] = m_z ** 2
    work["mass_z3"] = m_z ** 3

    mass_bin_source = first_existing(work, MASS_BIN_CANDIDATES)

    if mass_bin_source is not None:
        bins = work[mass_bin_source].astype(str)
        bin_policy = f"existing_column:{mass_bin_source}"
    else:
        bins = pd.qcut(
            work["present_log_mass"],
            q=n_mass_bins,
            labels=False,
            duplicates="drop",
        ).astype("Int64").astype(str)
        bin_policy = f"computed_qcut:{n_mass_bins}"

    dummies = pd.get_dummies(bins, prefix="mass_bin_fe", dummy_na=False)
    dummy_cols = list(dummies.columns)

    # Drop first dummy to avoid exact dummy-sum collinearity with intercept.
    if dummy_cols:
        dummies = dummies[dummy_cols[1:]]
        dummy_cols = list(dummies.columns)

    work = pd.concat([work, dummies.astype(float)], axis=1)

    strict_controls = ["mass_z", "mass_z2", "mass_z3", "present_acc_rate"] + dummy_cols

    provenance = {
        "target": "Yv",
        "target_formula": "log10(Vmax) - (1/3) log10(M_present)",
        "vmax_column": vmax_col,
        "log_mass_column": log_mass_col,
        "acc_rate_column": acc_col,
        "mass_bin_policy": bin_policy,
        "mass_bin_dummy_count": len(dummy_cols),
        "strict_controls": strict_controls,
    }

    return work, provenance, strict_controls

def design_matrix(df: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, list[str]]:
    pieces = [np.ones((len(df), 1), dtype=float)]
    names = ["intercept"]

    for col in columns:
        if col not in df.columns:
            continue

        z = standardize(df[col])
        if z.notna().sum() != len(df):
            continue

        sd = float(z.std(ddof=0))
        if not np.isfinite(sd) or sd <= 0:
            continue

        pieces.append(z.to_numpy(float).reshape(-1, 1))
        names.append(col)

    return np.column_stack(pieces), names

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

def fit_increment(df: pd.DataFrame, target: str, memory_col: str, controls: list[str]) -> dict:
    required = [target, memory_col] + controls
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"missing model columns: {missing}")

    work = df[required].copy()
    for col in required:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.replace([np.inf, -np.inf], np.nan).dropna()

    if len(work) < max(50, len(required) * 10):
        raise RuntimeError(f"too few complete rows: n={len(work)} required_cols={len(required)}")

    y = standardize(work[target]).to_numpy(float)
    m = standardize(work[memory_col]).to_numpy(float)

    X0, names0 = design_matrix(work, controls)
    X1 = np.column_stack([X0, m.reshape(-1, 1)])
    names1 = names0 + [memory_col]

    fit0 = ols(y, X0)
    fit1 = ols(y, X1)

    mi = names1.index(memory_col)

    return {
        "n_model": int(len(work)),
        "k_controls": int(fit0["k"]),
        "controls": ",".join(names0[1:]),
        "bic_controls": fit0["bic"],
        "bic_controls_plus_memory": fit1["bic"],
        "delta_bic_memory_vs_controls": fit1["bic"] - fit0["bic"],
        "r2_controls": fit0["r2"],
        "r2_controls_plus_memory": fit1["r2"],
        "delta_r2_memory_vs_controls": fit1["r2"] - fit0["r2"],
        "A_memory_standardized": float(fit1["beta"][mi]),
        "SE_memory_standardized": float(fit1["se"][mi]),
        "t_memory": float(fit1["t"][mi]),
    }

def conditional_shuffle(
    df: pd.DataFrame,
    target: str,
    memory_col: str,
    controls: list[str],
    permutations: int,
    seed: int,
) -> tuple[dict, list[dict]]:
    rng = np.random.default_rng(seed)

    required = [target, memory_col] + controls
    work = df[required].copy()
    for col in required:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.replace([np.inf, -np.inf], np.nan).dropna()

    y = standardize(work[target]).to_numpy(float)
    m = standardize(work[memory_col]).to_numpy(float)

    X0, names0 = design_matrix(work, controls)
    X1 = np.column_stack([X0, m.reshape(-1, 1)])

    fit0 = ols(y, X0)
    fit1 = ols(y, X1)

    beta_m, *_ = np.linalg.lstsq(X0, m, rcond=None)
    m_fit = X0 @ beta_m
    m_resid = m - m_fit

    observed_delta_bic = fit1["bic"] - fit0["bic"]
    observed_delta_r2 = fit1["r2"] - fit0["r2"]

    null_rows = []
    null_delta = []

    for i in range(permutations):
        m_null = m_fit + rng.permutation(m_resid)
        Xn = np.column_stack([X0, m_null.reshape(-1, 1)])
        fitn = ols(y, Xn)
        delta_bic = fitn["bic"] - fit0["bic"]
        delta_r2 = fitn["r2"] - fit0["r2"]
        null_delta.append(delta_bic)
        null_rows.append({
            "permutation": i,
            "null_delta_bic_memory_vs_strict_formation": float(delta_bic),
            "null_delta_r2_memory_vs_strict_formation": float(delta_r2),
        })

    null_delta = np.asarray(null_delta, dtype=float)
    p = float((1 + np.sum(null_delta <= observed_delta_bic)) / (permutations + 1))

    return {
        "shuffle_observed_delta_bic": float(observed_delta_bic),
        "shuffle_observed_delta_r2": float(observed_delta_r2),
        "null_delta_bic_q01": float(np.quantile(null_delta, 0.01)),
        "null_delta_bic_median": float(np.median(null_delta)),
        "null_delta_bic_q99": float(np.quantile(null_delta, 0.99)),
        "p_one_sided_more_negative": p,
        "shuffle_pass_p_le_0p01": bool(p <= 0.01),
        "shuffle_interpretation": (
            "memory_exceeds_conditional_shuffle_null"
            if p <= 0.01
            else "not_significant_against_conditional_shuffle_null"
        ),
    }, null_rows
