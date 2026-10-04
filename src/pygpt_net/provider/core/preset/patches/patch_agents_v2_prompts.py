"""Refresh unchanged stock Agents v2 prompts without replacing user settings."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


# Fingerprints of the shipped prompts replaced by the execution-policy refactor.
# Exact matching keeps edited prompts intact, regardless of profile/app version.
PREVIOUS_PROMPT_HASHES = {
    'agent_v2_brainstorm.json': ('85f2ffe19038ee8b7c694e5b0bce70310ac22d9cf9fc3ed416f57b8023bcd9d9', '21e70467eeb666d071379a23c0871f1459dea54370d9786cb49bbb9868bdfd76', 'e9b4954f93bc2564d33dafa0d2437bc4f6250604bc3e86f9929108e55851d3b0'),
    'agent_v2_coder.json': ('77fef9843f493bbce9a977269e6c88a5ae3aa0eced997be400a9cb2dfa611811', '2826210e33940644d71b5124d84b28e813e76c8e3730e0e87a66ae41f61bbeed', '0b347db94adb0b2c508e256a470aea07248e52b2c5cffa202fcbf4195c7b5205'),
    'agent_v2_cybersec.json': ('7787b9e111aedb7cf5a540e18b8dbd0f080869ef936f4c9237a3a1efa5fe1de8', '07678b4a8af8bef0747a8034585136d9f1d55b3132adc30c8026ff6048bfd9b4', 'ce71d506e57e2d3e73dde54fded57185935eefefd2dff33b7f5e42596fbb3830'),
    'agent_v2_osint.json': ('ad920c431bbac8fc6a7a595195b4f4f14d6d4e9decbd2d582220a356d1eea2eb', '199b417d9a3003baa6beea4e34bb40faeefbb78180d224eb624ab963ab1a4b50', 'fe2608cffaa7115c39bc106b9a1273cd3436f5253b914ed880ce877b80fbb391'),
    'agent_v2_pygpt.json': ('819bfac96e9e9bcd5e35f716eaca742a9ef93d2882f026595303f105f4b99056', '1b94a03a9dc3c88442d3fa00f667253f81ac0fb74215f90c1e582e663653b6e6', '1279b437dcdb80b7f2946f1d44dd490c31fad85a30615b643a4095a6aac3bd88', 'fc7d6cdf41f54820cf9f55278fbc64be5f69e93c07aa813c6a37028afad20427'),
    'agent_v2_researcher.json': ('83aceca942211a23d49b137c5c1427bebdb24a88d94ae93563b68fcf1cd26140', '79c2ea82153e0f939455229899c9bc2083614de8e23c48657435ab5135ee57f3', 'affd26d4f643c9c143af9a6e28db3b233a63218fe6e6556ad26824451e3369e4'),
    'agent_v2_scientist.json': ('0a2fe95da9e73572ee4538e0021dc2b04b0e9b8241553df02af1ec68ac4bfde1', '4882d3a8a3b89425a3d321f8f3aff0c2ed5a4e07ddff3c82fac356f478091586', 'af0326b833522a99675ab4316a1017f7d656163555ff5d4130a246f61da7420d'),
    'agent_v2_server_admin.json': ('807b5a30d1f2527dbf416ff6fa5b31e9af7b3618d25bbee4946cee663bb41e4d', '4ffe18edee23dac5165b052d11d1ce27af9b1f91ad62aeab55b80fcd47087d1d', '048684f4defd4953bfde02c7decdbfb37e93417dce536fc17367cc430e34ce2d'),
    'current.agent_v2.json': ('5e8504d99def28684ec230204709d12d9a53dc4772c8eb6eae443d6976c6fe3a', '1b94a03a9dc3c88442d3fa00f667253f81ac0fb74215f90c1e582e663653b6e6', '1279b437dcdb80b7f2946f1d44dd490c31fad85a30615b643a4095a6aac3bd88', 'fc7d6cdf41f54820cf9f55278fbc64be5f69e93c07aa813c6a37028afad20427'),
}


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self) -> bool:
        config = self.window.core.config
        user_dir = Path(config.get_user_dir("presets"))
        bundled_dir = Path(config.get_app_path()) / "data/config/presets"
        changed = False
        for filename, previous_hashes in PREVIOUS_PROMPT_HASHES.items():
            target = user_dir / filename
            if not target.is_file() or target.is_symlink():
                continue
            temporary = None
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                prompt = data.get("prompt")
                if not isinstance(prompt, str):
                    continue
                digest = hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()
                if digest not in previous_hashes or data.get("agent_v2") is not True:
                    continue
                bundled = json.loads((bundled_dir / filename).read_text(encoding="utf-8"))
                replacement = bundled["prompt"]
                if not isinstance(replacement, str) or not replacement.strip() or replacement == prompt:
                    continue
                # Change only the prompt: model, tools, IDs, user preferences,
                # metadata and unknown fields must survive the refresh.
                data["prompt"] = replacement
                with NamedTemporaryFile(mode="w", encoding="utf-8", dir=user_dir,
                                        prefix=".agents-v2-prompts-", delete=False) as stream:
                    temporary = Path(stream.name)
                    json.dump(data, stream, ensure_ascii=False, indent=4)
                    stream.write("\n")
                os.chmod(temporary, target.stat().st_mode & 0o777)
                os.replace(temporary, target)
                changed = True
            except Exception as exc:
                self.window.core.debug.log(exc)
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
        return changed
