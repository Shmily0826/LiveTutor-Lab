"""Install the reversible plane hook through the existing owned source entry."""
import shutil
from neko_lab_stage import LIVE, ROOT
from neko_lab_client import LabClient


def main():
    for root in (LIVE.parent,LIVE.parents[2]/'plugins'):
        shutil.copy2(ROOT/'scripts/neko_lab_runtime_plane.py',root/'lab_study_plane.py')
        (root/'study_companion/lab_bootstrap_plane.py').write_text('''from plugins.lab_study_runtime import install
install("study_companion")
from plugins.lab_study_plane import install as install_plane
install_plane()
from . import StudyCompanionPlugin
''',encoding='utf-8')
    manifest = LIVE/'plugin.toml'
    text = manifest.read_text(encoding='utf-8')
    before = 'plugins.study_companion.lab_bootstrap:StudyCompanionPlugin'
    if text.count(before) != 1:
        raise RuntimeError('Source entry not in expected deployed state')
    client = LabClient()
    client.request('/plugin/study_companion/stop','POST',{})
    manifest.write_text(text.replace(before,'plugins.study_companion.lab_bootstrap_plane:StudyCompanionPlugin'),encoding='utf-8')
    client.request('/plugins/refresh','POST',{},timeout=40)
    print(client.request('/plugin/study_companion/start','POST',{},timeout=40))


if __name__ == '__main__':
    main()
