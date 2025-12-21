"""
Performance Tracker for Voice AI pipeline metrics
Tracks latency, throughput, and quality metrics
"""
import time
import logging
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import (
    PERF_STT_MAX_LATENCY, PERF_LLM_MAX_LATENCY,
    PERF_TTS_MAX_LATENCY, PERF_E2E_MAX_LATENCY
)

logger = logging.getLogger(__name__)


@dataclass
class TimingMetric:
    """Single timing metric"""
    name: str
    start_time: float
    end_time: float = 0
    duration_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationTurn:
    """Metrics for a single conversation turn"""
    turn_number: int
    user_input: str
    agent_response: str
    stt_latency_ms: float = 0
    llm_latency_ms: float = 0
    tts_latency_ms: float = 0
    e2e_latency_ms: float = 0
    timestamp: str = ""


class PerformanceTracker:
    """Tracker for voice AI performance metrics"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.timings: List[TimingMetric] = []
        self.turns: List[ConversationTurn] = []
        self.active_timers: Dict[str, TimingMetric] = {}
        self.session_start: Optional[float] = None
        self.session_id: str = ""

    def start_session(self, session_id: str = None):
        """Start a new tracking session"""
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = time.time()
        self.timings.clear()
        self.turns.clear()
        self.active_timers.clear()
        logger.info(f"Started performance tracking session: {self.session_id}")

    def start_timer(self, name: str, metadata: Dict[str, Any] = None):
        """Start a named timer"""
        timer = TimingMetric(
            name=name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.active_timers[name] = timer
        logger.debug(f"Timer started: {name}")

    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a named timer and return duration in ms"""
        if name not in self.active_timers:
            logger.warning(f"Timer not found: {name}")
            return None

        timer = self.active_timers.pop(name)
        timer.end_time = time.time()
        timer.duration_ms = (timer.end_time - timer.start_time) * 1000

        self.timings.append(timer)
        logger.debug(f"Timer stopped: {name} = {timer.duration_ms:.2f}ms")

        return timer.duration_ms

    def record_turn(self, turn_number: int, user_input: str,
                   agent_response: str, stt_ms: float = 0,
                   llm_ms: float = 0, tts_ms: float = 0):
        """Record metrics for a conversation turn"""
        e2e_ms = stt_ms + llm_ms + tts_ms

        turn = ConversationTurn(
            turn_number=turn_number,
            user_input=user_input,
            agent_response=agent_response,
            stt_latency_ms=stt_ms,
            llm_latency_ms=llm_ms,
            tts_latency_ms=tts_ms,
            e2e_latency_ms=e2e_ms,
            timestamp=datetime.now().isoformat()
        )

        self.turns.append(turn)
        logger.info(
            f"Turn {turn_number}: STT={stt_ms:.0f}ms, "
            f"LLM={llm_ms:.0f}ms, TTS={tts_ms:.0f}ms, E2E={e2e_ms:.0f}ms"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        if not self.turns:
            return {"error": "No turns recorded"}

        stt_times = [t.stt_latency_ms for t in self.turns if t.stt_latency_ms > 0]
        llm_times = [t.llm_latency_ms for t in self.turns if t.llm_latency_ms > 0]
        tts_times = [t.tts_latency_ms for t in self.turns if t.tts_latency_ms > 0]
        e2e_times = [t.e2e_latency_ms for t in self.turns if t.e2e_latency_ms > 0]

        def calc_stats(times):
            if not times:
                return {"avg": 0, "min": 0, "max": 0, "p95": 0}
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            return {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "p95": sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
            }

        return {
            "session_id": self.session_id,
            "total_turns": len(self.turns),
            "session_duration_s": time.time() - self.session_start if self.session_start else 0,
            "stt_latency": calc_stats(stt_times),
            "llm_latency": calc_stats(llm_times),
            "tts_latency": calc_stats(tts_times),
            "e2e_latency": calc_stats(e2e_times)
        }

    def validate_performance(self) -> Dict[str, Any]:
        """Validate performance against thresholds"""
        summary = self.get_summary()

        results = {
            "passed": True,
            "failures": []
        }

        # Check STT latency
        if summary.get("stt_latency", {}).get("avg", 0) > PERF_STT_MAX_LATENCY:
            results["passed"] = False
            results["failures"].append(
                f"STT avg latency {summary['stt_latency']['avg']:.0f}ms > {PERF_STT_MAX_LATENCY}ms"
            )

        # Check LLM latency
        if summary.get("llm_latency", {}).get("avg", 0) > PERF_LLM_MAX_LATENCY:
            results["passed"] = False
            results["failures"].append(
                f"LLM avg latency {summary['llm_latency']['avg']:.0f}ms > {PERF_LLM_MAX_LATENCY}ms"
            )

        # Check TTS latency
        if summary.get("tts_latency", {}).get("avg", 0) > PERF_TTS_MAX_LATENCY:
            results["passed"] = False
            results["failures"].append(
                f"TTS avg latency {summary['tts_latency']['avg']:.0f}ms > {PERF_TTS_MAX_LATENCY}ms"
            )

        # Check E2E latency
        if summary.get("e2e_latency", {}).get("avg", 0) > PERF_E2E_MAX_LATENCY:
            results["passed"] = False
            results["failures"].append(
                f"E2E avg latency {summary['e2e_latency']['avg']:.0f}ms > {PERF_E2E_MAX_LATENCY}ms"
            )

        return results

    def export_report(self, output_path: str = None) -> str:
        """Export performance report to JSON file"""
        if not output_path:
            output_path = f"perf_report_{self.session_id}.json"

        report = {
            "session_id": self.session_id,
            "summary": self.get_summary(),
            "validation": self.validate_performance(),
            "turns": [
                {
                    "turn": t.turn_number,
                    "input": t.user_input,
                    "response": t.agent_response,
                    "stt_ms": t.stt_latency_ms,
                    "llm_ms": t.llm_latency_ms,
                    "tts_ms": t.tts_latency_ms,
                    "e2e_ms": t.e2e_latency_ms,
                    "timestamp": t.timestamp
                }
                for t in self.turns
            ],
            "timings": [
                {
                    "name": t.name,
                    "duration_ms": t.duration_ms,
                    "metadata": t.metadata
                }
                for t in self.timings
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Performance report exported: {output_path}")
        return output_path

    # Robot Framework Keywords
    def start_performance_session(self, session_id: str = None):
        """Robot Framework keyword to start session"""
        self.start_session(session_id)

    def start_performance_timer(self, name: str):
        """Robot Framework keyword to start timer"""
        self.start_timer(name)

    def stop_performance_timer(self, name: str) -> str:
        """Robot Framework keyword to stop timer"""
        duration = self.stop_timer(name)
        return str(duration) if duration else "0"

    def record_conversation_turn(self, turn_number: str, user_input: str,
                                agent_response: str, stt_ms: str = "0",
                                llm_ms: str = "0", tts_ms: str = "0"):
        """Robot Framework keyword to record turn"""
        self.record_turn(
            int(turn_number), user_input, agent_response,
            float(stt_ms), float(llm_ms), float(tts_ms)
        )

    def get_performance_summary(self) -> Dict[str, Any]:
        """Robot Framework keyword to get summary"""
        return self.get_summary()

    def performance_should_meet_thresholds(self):
        """Robot Framework keyword to validate performance"""
        result = self.validate_performance()
        if not result["passed"]:
            raise AssertionError(
                f"Performance validation failed: {', '.join(result['failures'])}"
            )
        return True

    def export_performance_report(self, output_path: str = None) -> str:
        """Robot Framework keyword to export report"""
        return self.export_report(output_path)

    def get_average_e2e_latency(self) -> str:
        """Robot Framework keyword to get avg E2E latency"""
        summary = self.get_summary()
        return str(summary.get("e2e_latency", {}).get("avg", 0))
