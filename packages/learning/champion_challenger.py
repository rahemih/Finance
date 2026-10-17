from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib, json, re
from typing import Mapping


class ChampionChallengerError(ValueError):
    """P18-F deterministic Champion/Challenger invariant failure."""


_SHA256=re.compile(r"^[0-9a-f]{64}$")
_SAFE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


def _bytes(value:object)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def _sha(value:str,*,field:str)->str:
    p=value.strip().lower()
    if _SHA256.fullmatch(p) is None:
        raise ChampionChallengerError(f"{field} must be lowercase SHA-256")
    return p


def _safe(value:str,*,field:str)->str:
    p=value.strip()
    if _SAFE.fullmatch(p) is None:
        raise ChampionChallengerError(f"{field} contains unsafe characters")
    return p


def _decimal(value:str,*,field:str)->Decimal:
    try:p=Decimal(value)
    except InvalidOperation as exc:raise ChampionChallengerError(f"{field} must be decimal") from exc
    if not p.is_finite():raise ChampionChallengerError(f"{field} must be finite")
    return p


def _metric_map(values:Mapping[str,str],*,field:str)->tuple[tuple[str,str],...]:
    out: list[tuple[str, str]] = []
    for k,v in sorted(values.items()):
        key=_safe(k,field=f"{field}.key"); d=_decimal(v,field=f"{field}.{k}")
        text="0" if d==0 else format(d.normalize(),"f")
        if "." in text:text=text.rstrip("0").rstrip(".")
        out.append((key,text))
    return tuple(out)


@dataclass(frozen=True,slots=True)
class EvaluationRecord:
    model_id:str
    dataset_id:str
    lineage_id:str
    performance_metrics:tuple[tuple[str,str],...]
    risk_metrics:tuple[tuple[str,str],...]

    @classmethod
    def create(cls,*,model_id:str,dataset_id:str,lineage_id:str,
               performance_metrics:Mapping[str,str],risk_metrics:Mapping[str,str])->"EvaluationRecord":
        return cls(_sha(model_id,field="model_id"),_sha(dataset_id,field="dataset_id"),
                   _sha(lineage_id,field="lineage_id"),
                   _metric_map(performance_metrics,field="performance"),
                   _metric_map(risk_metrics,field="risk"))

    def payload(self)->dict[str,object]:
        return {"model_id":self.model_id,"dataset_id":self.dataset_id,"lineage_id":self.lineage_id,
                "performance_metrics":[list(x) for x in self.performance_metrics],
                "risk_metrics":[list(x) for x in self.risk_metrics]}

    @property
    def evaluation_id(self)->str:
        return hashlib.sha256(_bytes(self.payload())).hexdigest()


@dataclass(frozen=True,slots=True)
class ComparisonPolicy:
    primary_metric:str
    minimum_improvement:str
    maximum_risk_degradation:str

    def __post_init__(self)->None:
        _safe(self.primary_metric,field="primary_metric")
        _decimal(self.minimum_improvement,field="minimum_improvement")
        if _decimal(self.maximum_risk_degradation,field="maximum_risk_degradation") < 0:
            raise ChampionChallengerError("maximum_risk_degradation must be non-negative")


@dataclass(frozen=True,slots=True)
class ComparisonResult:
    champion_evaluation_id:str
    challenger_evaluation_id:str
    recommendation:str
    primary_improvement:str
    risk_guard_pass:bool
    registry_mutation_authority:bool=False
    promotion_authority:bool=False
    automatic_live_promotion:bool=False
    live_trading:str="DISABLED"
    auto_trading:str="DISABLED"

    @property
    def result_id(self)->str:
        return hashlib.sha256(_bytes({
            "champion_evaluation_id":self.champion_evaluation_id,
            "challenger_evaluation_id":self.challenger_evaluation_id,
            "recommendation":self.recommendation,
            "primary_improvement":self.primary_improvement,
            "risk_guard_pass":self.risk_guard_pass,
            "registry_mutation_authority":self.registry_mutation_authority,
            "promotion_authority":self.promotion_authority,
            "automatic_live_promotion":self.automatic_live_promotion,
            "live_trading":self.live_trading,"auto_trading":self.auto_trading,
        })).hexdigest()


def compare(*,champion:EvaluationRecord,challenger:EvaluationRecord,policy:ComparisonPolicy)->ComparisonResult:
    if champion.dataset_id != challenger.dataset_id:
        raise ChampionChallengerError("champion and challenger must use same dataset")
    cp=dict(champion.performance_metrics); hp=dict(challenger.performance_metrics)
    cr=dict(champion.risk_metrics); hr=dict(challenger.risk_metrics)
    if set(cp)!=set(hp) or set(cr)!=set(hr):
        raise ChampionChallengerError("metric sets must match")
    if policy.primary_metric not in cp:
        raise ChampionChallengerError("primary metric missing")
    improvement=_decimal(hp[policy.primary_metric],field="challenger.primary")-_decimal(cp[policy.primary_metric],field="champion.primary")
    risk_cap=_decimal(policy.maximum_risk_degradation,field="maximum_risk_degradation")
    risk_ok=all(_decimal(hr[k],field=f"challenger.risk.{k}")-_decimal(cr[k],field=f"champion.risk.{k}") <= risk_cap for k in cr)
    recommended=risk_ok and improvement >= _decimal(policy.minimum_improvement,field="minimum_improvement")
    imp="0" if improvement==0 else format(improvement.normalize(),"f")
    if "." in imp:imp=imp.rstrip("0").rstrip(".")
    return ComparisonResult(
        champion_evaluation_id=champion.evaluation_id,
        challenger_evaluation_id=challenger.evaluation_id,
        recommendation="CHALLENGER_RECOMMENDED" if recommended else "KEEP_CHAMPION",
        primary_improvement=imp,
        risk_guard_pass=risk_ok,
    )
