#!/bin/bash
# Robot Framework Test Runner for Voice AI Platform
# Runs automated headless tests for 7 languages + VAD + SIP

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment variables (self-hosted, no cloud)
export LIVEKIT_URL="wss://192.168.20.62:7880"
export LIVEKIT_API_KEY="${LIVEKIT_API_KEY:-devkey}"
export LIVEKIT_API_SECRET="${LIVEKIT_API_SECRET:-secret}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Voice AI Platform - Robot Framework Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "LiveKit URL: $LIVEKIT_URL"
echo "Results Dir: $RESULTS_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create results directory
mkdir -p "${RESULTS_DIR}/${TIMESTAMP}"

# Function to run test suite
run_suite() {
    local suite_name=$1
    local suite_file=$2
    local tag_filter=$3

    echo -e "${YELLOW}Running: ${suite_name}${NC}"

    local output_dir="${RESULTS_DIR}/${TIMESTAMP}/${suite_name}"
    mkdir -p "${output_dir}"

    local cmd="robot \
        --outputdir ${output_dir} \
        --output output.xml \
        --log log.html \
        --report report.html \
        --loglevel DEBUG \
        ${suite_file}"

    if [ -n "$tag_filter" ]; then
        cmd="$cmd --include $tag_filter"
    fi

    echo "Command: $cmd"
    echo ""

    if eval $cmd; then
        echo -e "${GREEN}✓ ${suite_name} PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ ${suite_name} FAILED${NC}"
        return 1
    fi
}

# Main test execution
main() {
    local all_passed=true

    # Test 1: Multi-Language Conversations (7 languages)
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Test Suite 1: Multi-Language Conversations${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if ! run_suite "01_multilanguage" "${SCRIPT_DIR}/tests/01_multilanguage_conversation.robot" ""; then
        all_passed=false
    fi
    echo ""

    # Test 2: VAD Turn Detector (Critical)
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Test Suite 2: VAD Turn Detector (Critical)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if ! run_suite "02_vad_turn_detector" "${SCRIPT_DIR}/tests/02_vad_turn_detector.robot" ""; then
        all_passed=false
    fi
    echo ""

    # Final Summary
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Test Execution Summary${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Generate combined report
    local combined_output="${RESULTS_DIR}/${TIMESTAMP}/combined"
    mkdir -p "${combined_output}"

    echo "Generating combined report..."
    rebot \
        --outputdir "${combined_output}" \
        --output output.xml \
        --log log.html \
        --report report.html \
        --name "Voice AI Platform Tests" \
        "${RESULTS_DIR}/${TIMESTAMP}"/*/output.xml || true

    echo ""
    echo "Results saved to: ${RESULTS_DIR}/${TIMESTAMP}/"
    echo "Combined report: ${combined_output}/report.html"
    echo ""

    if $all_passed; then
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        return 0
    else
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}✗ SOME TESTS FAILED${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}Check logs at: ${combined_output}/log.html${NC}"
        return 1
    fi
}

# Run main
main "$@"
