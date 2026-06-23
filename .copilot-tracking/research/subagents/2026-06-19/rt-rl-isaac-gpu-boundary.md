<!-- markdownlint-disable-file -->
# rt-rl-isaac: RL / Isaac-Sim GPU boundary and CPU smoke ceiling

Captured by parent (research subagent read-only).

## Verdict
RL is GPU-coupled END-TO-END (Isaac Sim + Vulkan + NGC image). CPU smoke ceiling is shallow: import + arg-parse the launchers, import skrl_training, run the stubbed unit tests. No CPU RL env/training mode exists.

## GPU-only boundary (exact lines)
* RSL-RL: training/rl/scripts/rsl_rl/train.py:21 imports AppLauncher and :90 calls `AppLauncher(args_cli)` at MODULE-IMPORT level → cannot even `--help` without GPU.
* SKRL: training/rl/scripts/skrl_training.py defers — `from isaaclab.app import AppLauncher` inside run_training() (:1086), GPU trigger at `_initialize_simulation()` :785. The MODULE is CPU-importable; GPU only on run_training().
* Both need NVIDIA GPU + Vulkan (`NVIDIA_DRIVER_CAPABILITIES=all`, osmo/train.yaml:18; without it vkCreateDevice fails and shutdown hangs — gpu-configuration.md:90). Image nvcr.io/nvidia/isaac-lab:2.3.2 is **anonymously pullable** (verified live 2026-06-22: anonymous bearer token → manifest HTTP 200, no NGC key; 8.4 GB compressed). The repo's NGC-credential requirement (prerequisites.md:70) is for the GPU Operator catalog and pre-release nvcr.io/nvidia/osmo/* platform images, NOT this image — `create_nvcr_pull_secret` fires only for is_prerelease_tag/--use-acr (common.sh:303), and 2.3.2 is neither. So the CI blocker is GPU + disk, NOT auth: ~18-22 GB unpacked is heavy but feasible post-cleanup, but with no GPU you cannot run Isaac Sim, so pulling only verifies the digest resolves.

## CPU-safe surface (confirmed)
* launch.py, launch_rsl_rl.py: no isaaclab imports — fully CPU-safe arg-parse/--help (launch_rsl_rl.py:129 runs train via subprocess).
* skrl_training.py: importable; non-sim helpers + `_build_parser(MagicMock())` testable.
* skrl_mlflow_agent.py, simulation_shutdown.py, cli_args.py (isaaclab is TYPE_CHECKING-only): CPU-safe.
* Tests: all RL tests use conftest.load_training_module + sys.modules stubs; test_train_rsl_rl.py injects a `_StubAppLauncher` to bypass the :90 module-level GPU trigger (needs torch, no GPU). They cover MLflow wrappers, checkpoint logic, arg-parse, shutdown — NOT any sim step/rollout/policy gradient.

## Impossible on CPU
Any AppLauncher() instantiation, any Isaac gym env (gym.make("Isaac-*")), the RL training loop (sim-coupled), real simulation_shutdown against a live SimulationContext.

## Recommended
RL CPU smoke = import + arg-parse launchers + import skrl_training + run the stubbed training/tests suite. The real RL e2e MUST be the gated GPU tier (manual approval). Optional refactor: move rsl_rl/train.py's AppLauncher into a main() (like skrl) so the module imports + `--help` works without GPU. The isaac-lab image is anonymously pullable, so no ACR mirroring is needed for auth; mirror only if pull speed/reliability warrants it.
