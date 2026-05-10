import math

def detect_zscore_anomaly(values: list[float], threshold_z: float = 2.5) -> dict:
    if len(values) < 6:
        return {
            "method": "zscore",
            "is_anomaly": False,
            "reason": "not enough data (need at least 6)"
        }
        
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = math.sqrt(variance)
    
    if std == 0:
        return {
            "method": "zscore",
            "is_anomaly": False,
            "reason": "standard deviation is zero"
        }
        
    latest = values[-1]
    z_score = (latest - mean) / std
    
    is_anomaly = abs(z_score) > threshold_z
    direction = "spike" if z_score > 0 else "drop"
    
    return {
        "method": "zscore",
        "is_anomaly": is_anomaly,
        "z_score": float(z_score),
        "mean": float(mean),
        "std_dev": float(std),
        "latest_value": float(latest),
        "direction": direction if is_anomaly else None
    }

def detect_iqr_anomaly(values: list[float], multiplier: float = 1.5) -> dict:
    if len(values) < 4:
        return {
            "method": "iqr",
            "is_anomaly": False,
            "reason": "not enough data (need at least 4)"
        }
        
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    q1_idx = int(n * 0.25)
    q3_idx = int(n * 0.75)
    
    q1 = sorted_vals[q1_idx]
    q3 = sorted_vals[q3_idx]
    
    iqr = q3 - q1
    lower_fence = q1 - (multiplier * iqr)
    upper_fence = q3 + (multiplier * iqr)
    
    latest = values[-1]
    
    is_spike = latest > upper_fence
    is_drop = latest < lower_fence
    is_anomaly = is_spike or is_drop
    
    direction = None
    if is_spike:
        direction = "spike"
    elif is_drop:
        direction = "drop"
        
    return {
        "method": "iqr",
        "is_anomaly": is_anomaly,
        "latest_value": float(latest),
        "lower_fence": float(lower_fence),
        "upper_fence": float(upper_fence),
        "direction": direction
    }

def detect_moving_average_anomaly(values: list[float], window: int = 5, threshold_pct: float = 50.0) -> dict:
    """
    Moving Average Deviation (time-series aware)
    Checks if the latest value deviates from the moving average of the previous 'window' points
    by more than 'threshold_pct'.
    """
    if len(values) < window + 1:
        return {
            "method": "moving_average",
            "is_anomaly": False,
            "reason": f"not enough data (need at least {window + 1})"
        }
        
    latest = values[-1]
    previous_window = values[-(window + 1):-1]
    
    moving_avg = sum(previous_window) / len(previous_window)
    
    if moving_avg == 0:
        return {
            "method": "moving_average",
            "is_anomaly": False,
            "reason": "moving average is zero"
        }
        
    deviation_pct = ((latest - moving_avg) / moving_avg) * 100
    
    is_anomaly = abs(deviation_pct) > threshold_pct
    direction = "spike" if deviation_pct > 0 else "drop"
    
    return {
        "method": "moving_average",
        "is_anomaly": is_anomaly,
        "latest_value": float(latest),
        "moving_average": float(moving_avg),
        "deviation_pct": float(deviation_pct),
        "direction": direction if is_anomaly else None
    }
