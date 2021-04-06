

from tendril.libraries.projects.base import ProjectLibraryBase


class EDAProjectLibraryMixin(ProjectLibraryBase):
    def __init__(self, vctx=None):
        super(EDAProjectLibraryMixin, self).__init__(vctx)

    @property
    def cards(self):
        raise NotImplementedError

    @property
    def pcbs(self):
        raise NotImplementedError

    @property
    def cables(self):
        raise NotImplementedError

    @property
    def card_projects(self):
        return [x for x in self._projects if x.is_pcb]

    @property
    def cable_projects(self):
        return [x for x in self._projects if x.is_cable]

    def export_audit(self, name):
        super(EDAProjectLibraryMixin, self).export_audit(name)


def load(manager):
    pass
