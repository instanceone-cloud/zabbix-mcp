# System Integration Tests (SIT) for Zabbix MCP

Complete test pack for all 49 MCP tools against real Zabbix 7.0.23 instance.

## Quick Start

### 1. Set Up Environment

```bash
# Set Zabbix connection parameters
export ZABBIX_URL="http://192.168.1.101"
export ZABBIX_USERNAME="Admin"
export ZABBIX_PASSWORD="zabbix"
export ZABBIX_API_TOKEN="<your_api_token>"

# Or create .env file in project root
cat > .env << EOF
ZABBIX_URL=http://192.168.1.101
ZABBIX_API_TOKEN=<your_token>
EOF

# Install test dependencies
pip install pytest pytest-cov pytest-xdist
```

### 2. Run Tests

```bash
# Smoke tests (5 min) - quick validation
pytest tests/sit -m smoke -v

# Full SIT (30 min) - complete coverage
pytest tests/sit -v

# Security tests - validation + injection tests
pytest tests/sit -m security -v

# Specific test file
pytest tests/sit/test_host_lifecycle.py -v

# Single test
pytest tests/sit/test_host_lifecycle.py::TestHostLifecycle::test_create_host_success -v

# With output capture
pytest tests/sit -v -s
```

## Test Organization

### Directory Structure

```
tests/
├── conftest.py                  # Shared fixtures
├── sit/
│   ├── test_host_lifecycle.py  # Host CRUD + interfaces (8 tools, 18 tests)
│   ├── test_items_metrics.py   # Item management (3 tools, 8 tests)
│   ├── test_templates.py       # Template CRUD (3 tools, 8 tests)
│   ├── test_problems_alerts.py # Problem management (3 tools, 5 tests)
│   ├── test_triggers.py        # Trigger operations (5 tools, 10 tests)
│   ├── test_events.py          # Event management (2 tools, 3 tests)
│   ├── test_groups.py          # Host group management (4 tools, 6 tests)
│   ├── test_roles_users.py     # Role/user access control (4 tools, 8 tests)
│   ├── test_maintenance.py     # Maintenance windows (3 tools, 5 tests)
│   ├── test_system_status.py   # System monitoring (2 tools, 3 tests)
│   └── test_security_edge.py   # Edge cases + security (10+ tests)
├── README_SIT.md               # This file
```

### Fixtures Available

```python
# Standard fixtures from conftest.py

@pytest.fixture
def zabbix_client  # Authenticated Zabbix API client

@pytest.fixture
def test_environment  # Session-scoped test env (host group, host, template)

@pytest.fixture
def test_host  # Function-scoped test host (auto-cleaned up)

@pytest.fixture
def test_item  # Function-scoped test item on test_host

@pytest.fixture
def test_role  # Function-scoped test role

@pytest.fixture
def test_user  # Function-scoped test user
```

### Test Markers

```bash
# Run smoke tests only (5 min)
pytest -m smoke

# Run full SIT (30 min)
pytest -m full

# Run security tests
pytest -m security

# Exclude slow tests
pytest -m "not slow"

# Run smoke AND security
pytest -m "smoke or security"
```

## Coverage Goals

| Category | Tools | Tests | Status |
|----------|-------|-------|--------|
| Hosts | 8 | 18 | ✅ |
| Items | 3 | 8 | ⏳ |
| Templates | 4 | 8 | ⏳ |
| Problems | 3 | 5 | ⏳ |
| Triggers | 5 | 10 | ⏳ |
| Events | 2 | 3 | ⏳ |
| Groups | 4 | 6 | ⏳ |
| Roles/Users | 4 | 8 | ⏳ |
| Maintenance | 3 | 5 | ⏳ |
| System | 2 | 3 | ⏳ |
| Security/Edge | — | 10+ | ⏳ |
| **TOTAL** | **49** | **75+** | **In Progress** |

## Test Data Management

### Naming Convention

All test resources use prefixes for easy identification:
- Hosts: `sit-test-host-*`
- Items: `sit-test-item-*`
- Templates: `sit-test-template-*`
- Groups: `SIT_Test_Group_*`

### Auto-Cleanup

All fixtures auto-cleanup after test completes:
```python
yield resource_id

# Cleanup happens automatically
zabbix_client.call("host.delete", [host_id])
```

### Manual Cleanup (if needed)

```bash
# List test resources
curl -X POST http://192.168.1.101/api_jsonrpc.php \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "host.get",
    "params": {"filter": {"name": "sit-test*"}},
    "auth": "<token>",
    "id": 1
  }'

# Delete manually if needed
python scripts/cleanup_sit_resources.py
```

## Running Specific Suites

```bash
# Test host lifecycle only
pytest tests/sit/test_host_lifecycle.py -v

# Test items + templates
pytest tests/sit/test_items_metrics.py tests/sit/test_templates.py -v

# Test everything except slow tests
pytest tests/sit -m "not slow" -v

# Test with coverage report
pytest tests/sit --cov=src/zabbix_mcp --cov-report=html -v
# View report: open htmlcov/index.html
```

## Continuous Integration (GitHub Actions)

Automated tests run daily:

```bash
# Trigger manually
gh workflow run sit-tests.yml

# Check status
gh workflow view sit-tests.yml --json conclusion -q
```

## Troubleshooting

### Connection Issues

```bash
# Test Zabbix connection
python -c "from zabbix_mcp.client import ZabbixClient; c = ZabbixClient('http://192.168.1.101'); print('Connected' if c.token else 'Failed')"

# Check token validity
curl -X POST http://192.168.1.101/api_jsonrpc.php \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"host.get","auth":"<token>","id":1,"params":{"limit":1}}'
```

### Test Failures

```bash
# Run with verbose output
pytest tests/sit -vv -s

# Show all print statements
pytest tests/sit -s

# Stop on first failure
pytest tests/sit -x

# Drop into debugger on failure
pytest tests/sit --pdb
```

### Stuck Test Data

```bash
# List test resources in Zabbix
python -c "
from zabbix_mcp.client import ZabbixClient
import os

client = ZabbixClient(os.getenv('ZABBIX_URL'))
client.token = os.getenv('ZABBIX_API_TOKEN')

# Find test hosts
hosts = client.call('host.get', {'search': {'name': 'sit-test'}})
print(f'Found {len(hosts)} test hosts')
for h in hosts:
    print(f'  - {h[\"host\"]} ({h[\"hostid\"]})')
"
```

## Performance Expectations

| Test Suite | Time | Items | Status |
|------------|------|-------|--------|
| Smoke tests | 5 min | 12 | Quick validation |
| Full SIT | 30-45 min | 75+ | Complete coverage |
| Security tests | 10 min | 10+ | Injection + edge cases |
| Full with coverage | 60 min | 75+ | Detailed report |

## Best Practices

1. **Use fixtures** - Don't create resources manually, use provided fixtures
2. **Name uniquely** - Use timestamps for resource names to avoid conflicts
3. **Clean up** - All fixtures auto-cleanup, but verify afterward
4. **Run smoke first** - Quick validation before full SIT
5. **Check coverage** - Ensure 100% tool coverage
6. **Review failures** - Investigate test failures immediately

## Next Steps

1. **Set up GitHub Actions** - Automated daily runs
2. **Add more test files** - Create tests/sit/test_*.py for each tool category
3. **Track coverage** - Use codecov integration
4. **Add performance tests** - Benchmark response times
5. **Load testing** - Test concurrent operations

## Questions?

See `ZABBIX_MCP_SIT_STRATEGY.md` for detailed architecture and implementation guide.

## Test Results

Latest run results saved to: `test-results/latest.xml`

```bash
# View HTML report
open test-results/report.html

# View JUnit XML
cat test-results/latest.xml
```
