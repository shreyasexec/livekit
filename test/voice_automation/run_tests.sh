#!/bin/bash
# Voice AI Test Automation Runner
# Runs Robot Framework tests for Voice AI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
RESULTS_DIR="${SCRIPT_DIR}/results"
TESTS_DIR="${SCRIPT_DIR}/tests"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to run tests
run_tests() {
    local test_path=$1
    local output_dir=$2
    local tags=$3

    mkdir -p "${output_dir}"

    local robot_args=(
        --outputdir "${output_dir}"
        --loglevel DEBUG
        --pythonpath "${SCRIPT_DIR}"
        --pythonpath "${SCRIPT_DIR}/resources"
    )

    if [ -n "${tags}" ]; then
        robot_args+=(--include "${tags}")
    fi

    robot "${robot_args[@]}" "${test_path}"
}

# Activate virtual environment if it exists
if [ -d "${VENV_DIR}" ]; then
    source "${VENV_DIR}/bin/activate"
fi

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Parse command line argument
TEST_SUITE="${1:-help}"

case "${TEST_SUITE}" in
    api)
        print_status "${GREEN}" "=== Running API Tests ==="
        run_tests "${TESTS_DIR}/api" "${RESULTS_DIR}/api" ""
        ;;

    e2e)
        print_status "${GREEN}" "=== Running E2E Tests ==="
        run_tests "${TESTS_DIR}/e2e" "${RESULTS_DIR}/e2e" ""
        ;;

    webrtc)
        print_status "${GREEN}" "=== Running WebRTC Tests ==="
        run_tests "${TESTS_DIR}/webrtc" "${RESULTS_DIR}/webrtc" ""
        ;;

    livekit)
        print_status "${GREEN}" "=== Running LiveKit Tests ==="
        run_tests "${TESTS_DIR}/livekit" "${RESULTS_DIR}/livekit" ""
        ;;

    multilang)
        print_status "${GREEN}" "=== Running Multi-Language Tests ==="
        run_tests "${TESTS_DIR}/multilang" "${RESULTS_DIR}/multilang" ""
        ;;

    lang-english)
        print_status "${GREEN}" "=== Running English Language Tests ==="
        run_tests "${TESTS_DIR}/multilang/test_english.robot" "${RESULTS_DIR}/english" ""
        ;;

    lang-hindi)
        print_status "${GREEN}" "=== Running Hindi Language Tests ==="
        run_tests "${TESTS_DIR}/multilang/test_hindi.robot" "${RESULTS_DIR}/hindi" ""
        ;;

    lang-kannada)
        print_status "${GREEN}" "=== Running Kannada Language Tests ==="
        run_tests "${TESTS_DIR}/multilang/test_kannada.robot" "${RESULTS_DIR}/kannada" ""
        ;;

    lang-marathi)
        print_status "${GREEN}" "=== Running Marathi Language Tests ==="
        run_tests "${TESTS_DIR}/multilang/test_marathi.robot" "${RESULTS_DIR}/marathi" ""
        ;;

    smoke)
        print_status "${GREEN}" "=== Running Smoke Tests ==="
        run_tests "${TESTS_DIR}" "${RESULTS_DIR}/smoke" "smoke"
        ;;

    llm)
        print_status "${GREEN}" "=== Running LLM Tests ==="
        run_tests "${TESTS_DIR}/api/test_ollama_llm.robot" "${RESULTS_DIR}/llm" ""
        ;;

    tts)
        print_status "${GREEN}" "=== Running TTS Tests ==="
        run_tests "${TESTS_DIR}/api/test_piper_tts.robot" "${RESULTS_DIR}/tts" ""
        ;;

    pipeline)
        print_status "${GREEN}" "=== Running Pipeline Tests ==="
        run_tests "${TESTS_DIR}/api/test_full_pipeline.robot" "${RESULTS_DIR}/pipeline" ""
        ;;

    all)
        print_status "${GREEN}" "=== Running All Tests ==="

        # Run each suite
        for suite in api webrtc livekit multilang e2e; do
            print_status "${YELLOW}" "--- Running ${suite} tests ---"
            run_tests "${TESTS_DIR}/${suite}" "${RESULTS_DIR}/${suite}" "" || true
        done

        # Combine reports
        print_status "${GREEN}" "=== Combining Reports ==="
        rebot --outputdir "${RESULTS_DIR}/combined" \
            --name "Voice AI Test Suite" \
            "${RESULTS_DIR}"/*/output.xml 2>/dev/null || true
        ;;

    quick)
        print_status "${GREEN}" "=== Running Quick Tests (API only) ==="
        run_tests "${TESTS_DIR}/api/test_ollama_llm.robot" "${RESULTS_DIR}/quick" ""
        run_tests "${TESTS_DIR}/api/test_piper_tts.robot" "${RESULTS_DIR}/quick" "" || true
        ;;

    help|*)
        echo ""
        echo "Voice AI Test Automation Runner"
        echo ""
        echo "Usage: $0 <test-suite>"
        echo ""
        echo "Available test suites:"
        echo "  api           Run API tests (LLM, TTS, STT)"
        echo "  e2e           Run end-to-end scenario tests"
        echo "  webrtc        Run WebRTC UI tests"
        echo "  livekit       Run LiveKit agent tests"
        echo "  multilang     Run all multi-language tests"
        echo ""
        echo "Language-specific tests:"
        echo "  lang-english  Run English language tests"
        echo "  lang-hindi    Run Hindi language tests"
        echo "  lang-kannada  Run Kannada language tests"
        echo "  lang-marathi  Run Marathi language tests"
        echo ""
        echo "Component tests:"
        echo "  llm           Run LLM tests only"
        echo "  tts           Run TTS tests only"
        echo "  pipeline      Run full pipeline tests"
        echo ""
        echo "Other options:"
        echo "  smoke         Run smoke tests"
        echo "  quick         Run quick tests (API only)"
        echo "  all           Run all tests"
        echo "  help          Show this help"
        echo ""
        echo "Results are saved to: ${RESULTS_DIR}/<suite>/"
        echo ""
        ;;
esac

# Print summary
if [ -f "${RESULTS_DIR}/${TEST_SUITE}/output.xml" ]; then
    print_status "${GREEN}" ""
    print_status "${GREEN}" "=== Test Results ==="
    print_status "${GREEN}" "Output: ${RESULTS_DIR}/${TEST_SUITE}/output.xml"
    print_status "${GREEN}" "Report: ${RESULTS_DIR}/${TEST_SUITE}/report.html"
    print_status "${GREEN}" "Log: ${RESULTS_DIR}/${TEST_SUITE}/log.html"
fi
