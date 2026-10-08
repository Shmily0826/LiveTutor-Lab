from plugins.lab_study_runtime import install
install("study_companion")
from plugins.lab_study_plane import install as install_plane
install_plane()
from . import StudyCompanionPlugin
