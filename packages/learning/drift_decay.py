from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib, json, re

class DriftDecayError(ValueError):
    """P18-G deterministic drift/decay invariant failure."""

_SHA=re.compile(r"^[0-9a-f]{64}$")

def _bytes(v:object)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v:str,*,field:str)->str:
    p=v.strip().lower()
    if _SHA.fullmatch(p) is None:raise DriftDecayError(f"{field} must be lowercase SHA-256")
    return p
def _dec(v:str,*,field:str)->Decimal:
    try:p=Decimal(v)
    except InvalidOperation as exc:raise DriftDecayError(f"{field} must be decimal") from exc
    if not p.is_finite():raise DriftDecayError(f"{field} must be finite")
    return p
def _txt(v:Decimal)->str:
    if v==0:return "0"
    t=format(v.normalize(),"f")
    return t.rstrip("0").rstrip(".") if "." in t else t

@dataclass(frozen=True,slots=True)
class MonitoringWindow:
    strategy_id:str
    model_id:str
    dataset_id:str
    start_ns:int
    end_ns:int
    performance_score:str
    calibration_error:str
    distribution_drift_score:str
    def __post_init__(self)->None:
        _sha(self.strategy_id,field="strategy_id");_sha(self.model_id,field="model_id");_sha(self.dataset_id,field="dataset_id")
        if self.start_ns<0 or self.end_ns<=self.start_ns:raise DriftDecayError("invalid monitoring window time range")
        for f,v in (("performance_score",self.performance_score),("calibration_error",self.calibration_error),("distribution_drift_score",self.distribution_drift_score)):
            if _dec(v,field=f)<0:raise DriftDecayError(f"{f} must be non-negative")
    def payload(self)->dict[str,object]:
        return {"strategy_id":self.strategy_id,"model_id":self.model_id,"dataset_id":self.dataset_id,"start_ns":self.start_ns,"end_ns":self.end_ns,
                "performance_score":_txt(_dec(self.performance_score,field="performance_score")),
                "calibration_error":_txt(_dec(self.calibration_error,field="calibration_error")),
                "distribution_drift_score":_txt(_dec(self.distribution_drift_score,field="distribution_drift_score"))}
    @property
    def window_id(self)->str:return hashlib.sha256(_bytes(self.payload())).hexdigest()

@dataclass(frozen=True,slots=True)
class DriftPolicy:
    warn_distribution_drift:str
    decay_distribution_drift:str
    warn_performance_degradation:str
    decay_performance_degradation:str
    warn_calibration_degradation:str
    decay_calibration_degradation:str
    def __post_init__(self)->None:
        pairs=((self.warn_distribution_drift,self.decay_distribution_drift),(self.warn_performance_degradation,self.decay_performance_degradation),(self.warn_calibration_degradation,self.decay_calibration_degradation))
        for w,d in pairs:
            if _dec(w,field="warn")<0 or _dec(d,field="decay")<_dec(w,field="warn"):raise DriftDecayError("invalid warn/decay thresholds")

@dataclass(frozen=True,slots=True)
class DriftAssessment:
    baseline_window_id:str
    current_window_id:str
    severity:str
    performance_degradation:str
    calibration_degradation:str
    distribution_drift:str
    retrain_recommended:bool
    direct_retraining_authority:bool=False
    promotion_authority:bool=False
    automatic_live_promotion:bool=False
    live_trading:str="DISABLED"
    auto_trading:str="DISABLED"
    @property
    def assessment_id(self)->str:
        return hashlib.sha256(_bytes({"baseline_window_id":self.baseline_window_id,"current_window_id":self.current_window_id,
            "severity":self.severity,"performance_degradation":self.performance_degradation,
            "calibration_degradation":self.calibration_degradation,"distribution_drift":self.distribution_drift,
            "retrain_recommended":self.retrain_recommended,"direct_retraining_authority":self.direct_retraining_authority,
            "promotion_authority":self.promotion_authority,"automatic_live_promotion":self.automatic_live_promotion,
            "live_trading":self.live_trading,"auto_trading":self.auto_trading})).hexdigest()

def assess_drift(*,baseline:MonitoringWindow,current:MonitoringWindow,policy:DriftPolicy)->DriftAssessment:
    if (baseline.strategy_id,baseline.model_id)!=(current.strategy_id,current.model_id):
        raise DriftDecayError("monitoring lineage mismatch")
    if current.start_ns < baseline.end_ns:
        raise DriftDecayError("monitoring windows overlap or regress")
    perf=max(Decimal("0"),_dec(baseline.performance_score,field="baseline.performance")-_dec(current.performance_score,field="current.performance"))
    cal=max(Decimal("0"),_dec(current.calibration_error,field="current.calibration")-_dec(baseline.calibration_error,field="baseline.calibration"))
    drift=_dec(current.distribution_drift_score,field="current.drift")
    decay=(drift>=_dec(policy.decay_distribution_drift,field="decay.drift") or perf>=_dec(policy.decay_performance_degradation,field="decay.performance") or cal>=_dec(policy.decay_calibration_degradation,field="decay.calibration"))
    warn=(drift>=_dec(policy.warn_distribution_drift,field="warn.drift") or perf>=_dec(policy.warn_performance_degradation,field="warn.performance") or cal>=_dec(policy.warn_calibration_degradation,field="warn.calibration"))
    severity="DECAY" if decay else ("WARN" if warn else "NORMAL")
    return DriftAssessment(baseline.window_id,current.window_id,severity,_txt(perf),_txt(cal),_txt(drift),severity=="DECAY")
