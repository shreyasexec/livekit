#!/usr/bin/env python3
"""
Agent Log Parser - Extracts Component Timing from Agent Worker Logs

This script parses the agent-worker logs to extract detailed timing for each component:
- VAD: Voice Activity Detection (speech start/stop)
- STT: WhisperLiveKit transcription time
- LLM: Ollama response time
- TTS: Piper synthesis time (TTFB)

Usage:
  # Parse logs from docker-compose
  docker-compose logs agent-worker 2>&1 | python test/parse_agent_logs.py

  # Or save logs first
  docker-compose logs agent-worker > agent.log
  python test/parse_agent_logs.py agent.log

  # Real-time monitoring
  docker-compose logs -f agent-worker 2>&1 | python test/parse_agent_logs.py --live
"""

import sys
import re
from dataclasses import dataclass, field
from typing import List, Optional
from collections import defaultdict


@dataclass
class ConversationTurn:
    """Represents one conversation turn with all timing data."""
    turn_id: int = 0

    # VAD timing
    speech_start_time: str = ""
    speech_stop_time: str = ""
    speech_duration_s: float = 0.0

    # STT timing
    stt_transcript: str = ""
    stt_latency_s: float = 0.0

    # LLM timing
    stt_to_llm_s: float = 0.0  # Gap between STT final and LLM start
    llm_duration_s: float = 0.0

    # TTS timing
    tts_ttfb_s: float = 0.0  # Time to first byte

    # Total pipeline
    total_latency_s: float = 0.0  # Speech start to agent speaking


@dataclass
class TimingReport:
    """Aggregated timing report."""
    turns: List[ConversationTurn] = field(default_factory=list)

    # Averages
    avg_stt_latency: float = 0.0
    avg_llm_latency: float = 0.0
    avg_tts_ttfb: float = 0.0
    avg_total_latency: float = 0.0

    # Min/Max
    min_total_latency: float = float('inf')
    max_total_latency: float = 0.0


def parse_logs(lines, live_mode=False):
    """Parse agent logs and extract timing information."""
    report = TimingReport()
    current_turn = ConversationTurn()
    turn_count = 0

    # Regex patterns for log parsing
    patterns = {
        # [VAD] User started speaking
        'vad_start': re.compile(r'\[VAD\] User started speaking'),
        # [VAD] User stopped speaking (duration: 1.23s)
        'vad_stop': re.compile(r'\[VAD\] User stopped speaking \(duration: ([\d.]+)s\)'),
        # [TIMING] STT Final: 'text' (STT latency: 1.23s)
        'stt_final': re.compile(r'\[TIMING\] STT Final: \'([^\']*)\' \(STT latency: ([\d.]+)s\)'),
        # [STATE] listening -> thinking (STT->LLM: 0.12s)
        'stt_to_llm': re.compile(r'\[STATE\].*-> thinking \(STT->LLM: ([\d.]+)s\)'),
        # [STATE] thinking -> speaking (LLM: 1.23s, Total: 3.45s)
        'llm_complete': re.compile(r'\[STATE\].*-> speaking \(LLM: ([\d.]+)s, Total: ([\d.]+)s\)'),
        # [TTS] Time to first audio chunk: 0.123s
        'tts_ttfb': re.compile(r'\[TTS\] Time to first audio chunk: ([\d.]+)s'),
        # Timestamp at start of log line
        'timestamp': re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'),
    }

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract timestamp
        ts_match = patterns['timestamp'].match(line)
        timestamp = ts_match.group(1) if ts_match else ""

        # VAD - User started speaking (new turn begins)
        if patterns['vad_start'].search(line):
            # Save previous turn if it has data
            if current_turn.stt_transcript or current_turn.total_latency_s > 0:
                current_turn.turn_id = turn_count
                report.turns.append(current_turn)
                turn_count += 1

            current_turn = ConversationTurn()
            current_turn.speech_start_time = timestamp

            if live_mode:
                print(f"\n🎤 Turn {turn_count + 1}: User started speaking...")

        # VAD - User stopped speaking
        elif match := patterns['vad_stop'].search(line):
            current_turn.speech_stop_time = timestamp
            current_turn.speech_duration_s = float(match.group(1))

            if live_mode:
                print(f"   Speech duration: {current_turn.speech_duration_s:.2f}s")

        # STT Final transcript
        elif match := patterns['stt_final'].search(line):
            current_turn.stt_transcript = match.group(1)
            current_turn.stt_latency_s = float(match.group(2))

            if live_mode:
                print(f"   📝 STT: '{current_turn.stt_transcript[:50]}...' ({current_turn.stt_latency_s:.2f}s)")

        # STT -> LLM transition
        elif match := patterns['stt_to_llm'].search(line):
            current_turn.stt_to_llm_s = float(match.group(1))

            if live_mode:
                print(f"   ⏳ STT→LLM gap: {current_turn.stt_to_llm_s:.2f}s")

        # LLM complete -> TTS starting
        elif match := patterns['llm_complete'].search(line):
            current_turn.llm_duration_s = float(match.group(1))
            current_turn.total_latency_s = float(match.group(2))

            if live_mode:
                print(f"   🧠 LLM: {current_turn.llm_duration_s:.2f}s")
                print(f"   📊 Total: {current_turn.total_latency_s:.2f}s")

        # TTS Time to first byte
        elif match := patterns['tts_ttfb'].search(line):
            current_turn.tts_ttfb_s = float(match.group(1))

            if live_mode:
                print(f"   🔊 TTS TTFB: {current_turn.tts_ttfb_s:.3f}s")

    # Don't forget the last turn
    if current_turn.stt_transcript or current_turn.total_latency_s > 0:
        current_turn.turn_id = turn_count
        report.turns.append(current_turn)

    # Calculate aggregates
    if report.turns:
        stt_latencies = [t.stt_latency_s for t in report.turns if t.stt_latency_s > 0]
        llm_latencies = [t.llm_duration_s for t in report.turns if t.llm_duration_s > 0]
        tts_ttfbs = [t.tts_ttfb_s for t in report.turns if t.tts_ttfb_s > 0]
        total_latencies = [t.total_latency_s for t in report.turns if t.total_latency_s > 0]

        if stt_latencies:
            report.avg_stt_latency = sum(stt_latencies) / len(stt_latencies)
        if llm_latencies:
            report.avg_llm_latency = sum(llm_latencies) / len(llm_latencies)
        if tts_ttfbs:
            report.avg_tts_ttfb = sum(tts_ttfbs) / len(tts_ttfbs)
        if total_latencies:
            report.avg_total_latency = sum(total_latencies) / len(total_latencies)
            report.min_total_latency = min(total_latencies)
            report.max_total_latency = max(total_latencies)

    return report


def print_report(report: TimingReport):
    """Print formatted timing report."""
    print("\n" + "=" * 80)
    print("AGENT TIMING ANALYSIS REPORT")
    print("=" * 80)

    if not report.turns:
        print("\n⚠️  No conversation turns found in logs.")
        print("   Make sure the agent is running and processing speech.")
        return

    # Summary
    print(f"\n📊 SUMMARY ({len(report.turns)} conversation turns)")
    print("-" * 60)

    print(f"\n  Component Breakdown (averages):")
    print(f"  ┌─────────────────────────────────────────────────────────┐")
    print(f"  │ Component          │ Avg Latency │ % of Total          │")
    print(f"  ├─────────────────────────────────────────────────────────┤")

    total = report.avg_total_latency if report.avg_total_latency > 0 else 1

    stt_pct = (report.avg_stt_latency / total * 100) if total > 0 else 0
    llm_pct = (report.avg_llm_latency / total * 100) if total > 0 else 0
    tts_pct = (report.avg_tts_ttfb / total * 100) if total > 0 else 0

    print(f"  │ STT (WhisperLive)  │ {report.avg_stt_latency:>7.2f}s   │ {stt_pct:>5.1f}% {'█' * int(stt_pct/5):<20} │")
    print(f"  │ LLM (Ollama)       │ {report.avg_llm_latency:>7.2f}s   │ {llm_pct:>5.1f}% {'█' * int(llm_pct/5):<20} │")
    print(f"  │ TTS (Piper) TTFB   │ {report.avg_tts_ttfb:>7.3f}s   │ {tts_pct:>5.1f}% {'█' * int(tts_pct/5):<20} │")
    print(f"  ├─────────────────────────────────────────────────────────┤")
    print(f"  │ TOTAL              │ {report.avg_total_latency:>7.2f}s   │ 100.0%              │")
    print(f"  └─────────────────────────────────────────────────────────┘")

    print(f"\n  Latency Range:")
    print(f"    Min: {report.min_total_latency:.2f}s | Max: {report.max_total_latency:.2f}s")

    # Identify bottleneck
    print(f"\n🎯 BOTTLENECK ANALYSIS:")
    components = [
        ("STT (WhisperLive CPU)", report.avg_stt_latency, stt_pct),
        ("LLM (Ollama)", report.avg_llm_latency, llm_pct),
        ("TTS (Piper)", report.avg_tts_ttfb, tts_pct),
    ]

    bottleneck = max(components, key=lambda x: x[1])
    print(f"  ⚠️  Primary bottleneck: {bottleneck[0]}")
    print(f"      Consuming {bottleneck[2]:.1f}% of total latency ({bottleneck[1]:.2f}s)")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if report.avg_stt_latency > 2.0:
        print(f"  • STT is slow ({report.avg_stt_latency:.2f}s) - Consider:")
        print(f"    - GPU acceleration for WhisperLive (CUDA)")
        print(f"    - Smaller Whisper model (tiny/base instead of small)")
        print(f"    - Reduce buffer-trimming-sec in docker-compose")

    if report.avg_llm_latency > 2.0:
        print(f"  • LLM is slow ({report.avg_llm_latency:.2f}s) - Consider:")
        print(f"    - Smaller model (llama3.1:7b)")
        print(f"    - GPU acceleration for Ollama")
        print(f"    - Reducing system prompt length")

    if report.avg_tts_ttfb > 0.5:
        print(f"  • TTS TTFB is slow ({report.avg_tts_ttfb:.3f}s) - Consider:")
        print(f"    - Faster Piper voice (low quality vs medium)")
        print(f"    - Connection pooling (already implemented)")

    if report.avg_total_latency < 3.0:
        print(f"  ✓ Total latency ({report.avg_total_latency:.2f}s) is acceptable for voice conversation")
    elif report.avg_total_latency > 5.0:
        print(f"  ⚠️  Total latency ({report.avg_total_latency:.2f}s) is too high for natural conversation")
        print(f"      Target: < 3s for good user experience")

    # Per-turn details
    print(f"\n📋 PER-TURN BREAKDOWN:")
    print(f"  {'#':<4} {'Transcript':<35} {'STT':<8} {'LLM':<8} {'TTS':<8} {'Total':<8}")
    print(f"  {'-'*4} {'-'*35} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for turn in report.turns:
        transcript = turn.stt_transcript[:32] + "..." if len(turn.stt_transcript) > 35 else turn.stt_transcript
        stt = f"{turn.stt_latency_s:.2f}s" if turn.stt_latency_s > 0 else "N/A"
        llm = f"{turn.llm_duration_s:.2f}s" if turn.llm_duration_s > 0 else "N/A"
        tts = f"{turn.tts_ttfb_s:.3f}s" if turn.tts_ttfb_s > 0 else "N/A"
        total = f"{turn.total_latency_s:.2f}s" if turn.total_latency_s > 0 else "N/A"

        print(f"  {turn.turn_id + 1:<4} {transcript:<35} {stt:<8} {llm:<8} {tts:<8} {total:<8}")

    print("\n" + "=" * 80)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse agent worker logs for timing analysis")
    parser.add_argument("logfile", nargs="?", help="Log file to parse (or pipe from stdin)")
    parser.add_argument("--live", action="store_true", help="Live monitoring mode")
    args = parser.parse_args()

    if args.logfile:
        with open(args.logfile, 'r') as f:
            lines = f.readlines()
    else:
        lines = sys.stdin.readlines()

    if args.live:
        print("📊 Live Agent Timing Monitor")
        print("   Parsing logs as they arrive...")
        report = parse_logs(lines, live_mode=True)
    else:
        report = parse_logs(lines, live_mode=False)

    print_report(report)


if __name__ == "__main__":
    main()
