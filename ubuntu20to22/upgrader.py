# Copyright 2024. Plesk International GmbH. All rights reserved.

import argparse
import os
import typing

from pleskdistup import actions
from pleskdistup.common import action, feedback, php, version, strings
from pleskdistup.phase import Phase
from pleskdistup.upgrader import dist, DistUpgrader, DistUpgraderFactory, PathType

import ubuntu20to22.config


class Ubuntu20to22Upgrader(DistUpgrader):
    _distro_from = dist.Ubuntu("20")
    _distro_to = dist.Ubuntu("22")

    def __init__(self):
        super().__init__()

        self.downgrade_allowed = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(From {self._distro_from}, To {self._distro_to})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"

    @classmethod
    def supports(
        cls,
        from_system: typing.Optional[dist.Distro] = None,
        to_system: typing.Optional[dist.Distro] = None
    ) -> bool:
        return (
            (from_system is None or cls._distro_from == from_system)
            and (to_system is None or cls._distro_to == to_system)
        )

    @property
    def upgrader_name(self) -> str:
        return "Plesk::Ubuntu20to22Upgrader"

    @property
    def upgrader_version(self) -> str:
        return ubuntu20to22.config.revision

    @property
    def issues_url(self) -> str:
        return "https://github.com/plesk/ubuntu20to22/issues"

    def prepare_feedback(
        self,
        feed: feedback.Feedback,
    ) -> feedback.Feedback:
        feed.collect_actions += [
            feedback.collect_installed_packages_apt,
            feedback.collect_installed_packages_dpkg,
            feedback.collect_apt_policy,
            feedback.collect_plesk_version,
            feedback.collect_kernel_modules,
        ]
        return feed

    def construct_actions(
        self,
        upgrader_bin_path: PathType,
        options: typing.Any,
        phase: Phase
    ) -> typing.Dict[str, typing.List[action.ActiveAction]]:
        new_os = str(self._distro_to)
        return {
            "Prepare": [
                actions.HandleConversionStatus(
                    options.status_flag_path,
                    options.completion_flag_path,
                ),
                actions.AddFinishSshLoginMessage(new_os),  # Executed at the finish phase only
                actions.AddInProgressSshLoginMessage(new_os),
                actions.DisablePleskSshBanner(),
                actions.RepairPleskInstallation(),  # Executed at the finish phase only
                actions.UninstallTuxcareEls(),
                actions.UpgradePackages(allow_downgrade=self.downgrade_allowed),
                actions.UpdatePlesk(),
                actions.AddUpgradeSystemdService(
                    os.path.abspath(upgrader_bin_path),
                    options,
                ),
                actions.ConfigureMariadb({
                    "mysqld.bind-address": {
                        "prepare": actions.ConfigValueReplacer(
                            new_value="127.0.0.1",
                            old_value="::ffff:127.0.0.1",
                        ),
                        "revert": actions.ConfigValueReplacer(
                            new_value="::ffff:127.0.0.1",
                            old_value="127.0.0.1",
                        ),
                    },
                    "mysqld.innodb_fast_shutdown": {
                        "prepare": actions.ConfigValueReplacer(
                            new_value="0",
                            old_value=None,
                        ),
                        "revert": actions.ConfigValueReplacer(
                            new_value=None,
                            old_value="0",
                        ),
                    },
                }),
                actions.HoldMariadbAmbientCapabilities(),
                actions.EnableEnhancedSecurityMode(),
            ],
            "Switch repositories": [
                # UpdateLegacyPhpRepositories specific for distupgrades where
                #  we support following PHP versions: PHP 7.1, 7.2, 7.3.
                actions.UpdateLegacyPhpRepositories(self._distro_from, self._distro_to),
                actions.AdoptAptRepositoriesUbuntu([
                    strings.create_replace_string_function('focal', 'jammy'),
                    strings.create_replace_regexp_function(r'(http|https)://([^/]+)/(.*\b)20\.04(\b.*)', '\g<1>://\g<2>/\g<3>22.04\g<4>')
                    ], name="modify apt repositories to new OS"
                ),
                actions.SwitchPleskRepositories(to_os_version="22.04"),
            ],
            "Dist-upgrade": [
                actions.DoDistupgrade(),
            ],
            "Update Plesk": [
                actions.UpdatePlesk(update_cmd_args=["--skip-cleanup"]),
            ],
            "Update Plesk extensions": [
                actions.UpdatePleskExtensions([
                    "panel-migrator", "site-import", "docker", "grafana",
                    "ruby",
                ]),
            ],
            "Finishing actions": [
                actions.Reboot(
                    prepare_next_phase=Phase.FINISH,
                    name="reboot and perform finishing actions",
                ),
                actions.Reboot(
                    prepare_reboot=None,
                    post_reboot=action.RebootType.AFTER_LAST_STAGE,
                    name="final reboot",
                ),
            ],
        }

    def get_check_actions(
        self,
        options: typing.Any,
        phase: Phase,
    ) -> typing.List[action.CheckAction]:
        if phase is Phase.FINISH:
            return []

        PHP_VERSIONS_SUPPORTED_BY_UBUNTU_22 = [str(php) for php in php.get_known_php_versions() if php >= version.PHPVersion("7.0")]

        return [
            actions.AssertMinPleskVersion("18.0.44"),
            actions.AssertPleskInstallerNotInProgress(),
            actions.AssertInstalledPhpVersionsInList(PHP_VERSIONS_SUPPORTED_BY_UBUNTU_22),
            actions.AssertPhpVersionsUsedByWebsitesInList(PHP_VERSIONS_SUPPORTED_BY_UBUNTU_22),
            actions.AssertPhpVersionsUsedByCronInList(PHP_VERSIONS_SUPPORTED_BY_UBUNTU_22),
            actions.AssertDpkgNotLocked(),
            actions.AssertNotInContainer(),
            actions.AssertPleskComponents(not_installed=["mailman"]),
            actions.AssertMinFreeDiskSpace(
                {
                    # Space requirements in bytes
                    "/boot": 150 * 1024**2,
                    "/opt": 150 * 1024**2,
                    "/usr": 1800 * 1024**2,
                    "/var": 2000 * 1024**2,
                }
            ),
            actions.AssertRepositorySubstitutionAvailable(
                target_repository_file="/etc/apt/sources.list.d/mariadb.list",
                substitution_rule=strings.create_replace_string_function("focal", "jammy"),
                name="asserting mariadb repository substitution available",
                description_addition="""\tCurrent MariaDB repository is not available on the target platform.
\tTo proceed with dist-upgrade update MariaDB to version 10.6 or higher using the official repository,
\tor configure a custom repository that supports Ubuntu 22.04.
""",
            )
        ]

    def parse_args(self, args: typing.Sequence[str]) -> None:
        DESC_MESSAGE = f"""Use this upgrader to dist-upgrade an {self._distro_from} server with Plesk to {self._distro_to}. The process consists of the following general stages:
The process consists of the following general stages:

-- Preparation (about 5 minutes) - The OS is prepared for the conversion.
-- Conversion (about 15 minutes) - Plesk and system dist-upgrade is performed.
-- Finalization (about 5 minutes) - The server is returned to normal operation.

The system will be rebooted after each of the stages, so reboot times
should be added to get the total time estimate.

To see the detailed plan, run the utility with the --show-plan option.

For assistance, submit an issue here {self.issues_url}
and attach the feedback archive generated with --prepare-feedback or at least
the log file.
"""
        parser = argparse.ArgumentParser(
            usage=argparse.SUPPRESS,
            description=DESC_MESSAGE,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False,
        )
        parser.add_argument(
            "-h", "--help", action="help", default=argparse.SUPPRESS,
            help=argparse.SUPPRESS,
        )
        parser.add_argument("--allow-downgrade", action="store_true", dest="downgrade_allowed", default=False,
                            help="Allow packages downgrade. In some cases, apt may downgrade packages to the previous version during the dist-upgrade.")
        options = parser.parse_args(args)

        self.downgrade_allowed = options.downgrade_allowed


class Ubuntu20to22Factory(DistUpgraderFactory):
    def __init__(self):
        super().__init__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(upgrader_name={self.upgrader_name})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} (creates {self.upgrader_name})"

    def supports(
        self,
        from_system: typing.Optional[dist.Distro] = None,
        to_system: typing.Optional[dist.Distro] = None
    ) -> bool:
        return Ubuntu20to22Upgrader.supports(from_system, to_system)

    @property
    def upgrader_name(self) -> str:
        return "Plesk::Ubuntu20to22Upgrader"

    def create_upgrader(self, *args, **kwargs) -> DistUpgrader:
        return Ubuntu20to22Upgrader(*args, **kwargs)
