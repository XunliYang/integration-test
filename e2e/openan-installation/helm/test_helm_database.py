import pytest

from utils.env import install_config
from utils.helm_install import (
    configure_online_helm,
    ensure_metallb_pool,
    exercise_agent_data_path,
    helm_install_values,
    namespace_resources,
    platform_base,
    require_helm_env,
    statefulsets,
    uninstall_online_helm,
    wait_pods_ready,
)
from utils.shell import kubectl, kubectl_jsonpath

pytestmark = [
    getattr(pytest.mark, "openan-installation"),
    getattr(pytest.mark, "with-workload-cluster"),
    getattr(pytest.mark, "registry-center"),
    getattr(pytest.mark, "orchestration-center"),
    pytest.mark.P1,
    pytest.mark.full,
]

SERVICES = ("registry-center", "orchestration-center", "openan-frontend")


def _deploy_with_values(cfg, evidence_stem: str, **wizard_options) -> None:
    configure = configure_online_helm(cfg, evidence_stem=f"{evidence_stem}-configure", **wizard_options)
    assert configure.exit_code == 0, configure.output
    pool = ensure_metallb_pool(cfg)
    assert pool is None or pool.exit_code == 0, pool.output if pool else ""
    helm = helm_install_values(cfg)
    assert helm.exit_code == 0, helm.output


def _assert_agent_data_path() -> None:
    register_status, register_body, query_status, query_body = exercise_agent_data_path(platform_base(""))
    assert register_status == "201", f"agent registration failed: {register_status} {register_body}"
    assert query_status == "200", f"agent query failed: {query_status} {query_body}"


def _assert_uninstalled(uninstall) -> None:
    assert uninstall.exit_code == 0, uninstall.output
    assert namespace_resources() == [], namespace_resources()


@getattr(pytest.mark, "FIT-openan-installation-db-type-001")
@getattr(pytest.mark, "26-winter")
def test_bundled_database_type_postgresql_deploys_postgres_and_services_work(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    _deploy_with_values(cfg, "db-type-001")
    assert wait_pods_ready(SERVICES + ("openan-postgres",)), kubectl(["-n", "openan", "get", "pods"]).output
    assert statefulsets() == ["openan-postgres"], statefulsets()
    _assert_agent_data_path()
    _assert_uninstalled(uninstall_online_helm(cfg))


@getattr(pytest.mark, "FIT-openan-installation-db-type-002")
@getattr(pytest.mark, "26-winter")
def test_bundled_database_type_mysql_deploys_mysql_and_services_work(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    _deploy_with_values(cfg, "db-type-002", database="mysql")
    assert wait_pods_ready(SERVICES + ("openan-mysql",)), kubectl(["-n", "openan", "get", "pods"]).output
    assert statefulsets() == ["openan-mysql"], statefulsets()
    _assert_agent_data_path()
    _assert_uninstalled(uninstall_online_helm(cfg))


@getattr(pytest.mark, "FIT-openan-installation-db-type-003")
@getattr(pytest.mark, "26-winter")
def test_external_database_type_deploys_no_in_cluster_db_and_passes_type_through(require_profile, cleanup):
    require_profile("cluster-ops")
    cfg = install_config()
    require_helm_env(cfg)
    if not (cfg.external_db_type and cfg.external_db_host and cfg.external_db_port and cfg.external_db_password):
        pytest.skip("OPENAN_INSTALL_EXTERNAL_DB_TYPE / _HOST / _PORT / _PASSWORD are not set")
    cleanup.add("uninstall online helm", uninstall_online_helm, cfg)
    external_db = {"type": cfg.external_db_type, "host": cfg.external_db_host, "port": cfg.external_db_port}
    _deploy_with_values(cfg, "db-type-003", external_db=external_db)
    assert wait_pods_ready(SERVICES), kubectl(["-n", "openan", "get", "pods"]).output
    assert statefulsets() == [], f"an in-cluster database was deployed: {statefulsets()}"
    mode = kubectl(["-n", "openan", "exec", "deploy/registry-center", "--", "printenv", "PERSISTENCE_MODE"], timeout=120)
    assert mode.exit_code == 0 and mode.stdout.strip() == cfg.external_db_type, mode.output
    secret = kubectl_jsonpath(
        "deploy/registry-center",
        "{.spec.template.spec.containers[0].env[?(@.name==\"DB_PASSWORD\")].valueFrom.secretKeyRef.name}",
    ).stdout.strip()
    assert secret == "openan-rc-db", f"registry-center reads its DB password from {secret!r}"
    _assert_agent_data_path()
    _assert_uninstalled(uninstall_online_helm(cfg))
