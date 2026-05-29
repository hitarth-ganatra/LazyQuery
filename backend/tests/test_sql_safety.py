from app.services.sql_safety import SqlSafetyError, SqlSafetyValidator


def test_rejects_mutation_keyword() -> None:
    validator = SqlSafetyValidator(max_rows=100)
    try:
        validator.validate_and_rewrite("DELETE FROM users", 20, 0)
        assert False, "Expected SqlSafetyError"
    except SqlSafetyError:
        assert True


def test_applies_limit_offset() -> None:
    validator = SqlSafetyValidator(max_rows=50)
    sql, warnings = validator.validate_and_rewrite("SELECT * FROM users", 80, 10)
    assert "LIMIT 50 OFFSET 10" in sql
    assert warnings
