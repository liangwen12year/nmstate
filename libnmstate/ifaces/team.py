#
# Copyright (c) 2020 Red Hat, Inc.
#
# This file is part of nmstate
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#

from operator import itemgetter

from libnmstate.schema import Team

from .base_iface import BaseIface


class TeamIface(BaseIface):
    @property
    def port(self):
        ports = self.raw.get(Team.CONFIG_SUBTREE, {}).get(
            Team.PORT_SUBTREE, []
        )
        return [p[Team.Port.NAME] for p in ports]

    @property
    def is_controller(self):
        return True

    @property
    def is_virtual(self):
        return True

    def sort_port(self):
        if self.port:
            self.raw[Team.CONFIG_SUBTREE][Team.PORT_SUBTREE].sort(
                key=itemgetter(Team.Port.NAME)
            )

    def remove_port(self, port_name):
        if self.port:
            port_config = self.raw[Team.CONFIG_SUBTREE][Team.PORT_SUBTREE]
            self.raw[Team.CONFIG_SUBTREE][Team.PORT_SUBTREE] = [
                s for s in port_config if s[Team.Port.NAME] != port_name
            ]
        self.sort_port()
