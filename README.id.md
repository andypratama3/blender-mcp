# Blender MCP Agent Kit

Kontrol Blender **live** untuk agent AI, dibangun di atas **MCP bridge resmi Blender**.
Repo ini bukan MCP server dan tidak memodifikasi Blender. Isinya: satu skill, installer
yang bisa jalan sendiri, dan verifikasi yang membuktikan rig benar-benar menggerakkan
mesh.

[![CI](https://github.com/andypratama3/blender-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/andypratama3/blender-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Blender](https://img.shields.io/badge/Blender-5.2%2B-orange)](https://www.blender.org)

> **Bukan `ahujasid/blender-mcp`.** Itu MCP server komunitas. Kit ini memakai add-on
> resmi Blender Lab `bl_ext.blenderlab.mcp` (default `127.0.0.1:9876`). Jangan jalankan
> keduanya di port yang sama.

---

## Isi repo

| Bagian | Fungsi |
|---|---|
| `skills/blender-live-rigging/` | Skill agent: rig dan edit di Blender yang **sedang terbuka**, tanpa batch headless, tanpa render tak diminta |
| `scripts/doctor.py` | Satu perintah untuk cek Blender, add-on, socket, dan skill terpasang |
| `scripts/install.sh` / `install.ps1` | Install skill idempoten untuk OpenCode, Claude Code, Codex, Cursor, Gemini CLI, Copilot |
| `docs/` | Protokol bridge, install per OS, playbook rigging, verifikasi angka, kebijakan render, troubleshooting |
| `examples/crimping-tool/` | Studi kasus nyata + snippet pengukur metriknya |
| `.github/` | CI, form issue, template PR, panduan kontribusi dan keamanan |

Tanpa dependency Python. Tanpa telemetry. Semua script memakai standard library.

---

## Setup 60 detik (manusia)

```bash
git clone https://github.com/andypratama3/blender-mcp.git
cd blender-mcp
./scripts/install.sh --agent opencode      # atau claude, agents, cursor, gemini, copilot, all

open -a Blender --args --online-mode "/path/absolut/file.blend"

python3 scripts/doctor.py                  # harus 6 PASS, exit 0
```

Linux:

```bash
blender --online-mode "/path/file.blend" &
python3 scripts/doctor.py
```

Windows (PowerShell):

```powershell
.\scripts\install.ps1 -Agent opencode
& "C:\Program Files\Blender Foundation\Blender 5.4\blender.exe" --online-mode "C:\path\file.blend"
python .\scripts\doctor.py
```

Setelah itu bicara normal ke agent: *"Rig tool ini di Blender saya yang terbuka dan
buktikan deformasinya dengan angka."*

---

## Setup 60 detik (agent)

Tempel ini ke OpenCode, Claude Code, Codex, Cursor, Gemini CLI, atau Copilot:

```text
Set up https://github.com/andypratama3/blender-mcp for me.

1. Clone it to ~/Development/blender-mcp (skip if it exists, then git pull).
2. Read AGENTS.md and follow it exactly.
3. Install the skill with scripts/install.sh --agent <my-agent>.
4. Ask me to start Blender with --online-mode if the bridge is down; never kill it.
5. Run python3 scripts/doctor.py and show me the raw output.
6. Stop there and report what passed, what failed, and the exact next command.
Do not render anything unless I explicitly ask.
```

`AGENTS.md` ditulis untuk mesin: perintah persis, output yang diharapkan, cabang
kegagalan, dan aturan keselamatan. Contoh run yang benar ada di `docs/AGENT_SETUP.md`.

---

## Kebutuhan

| Item | Detail |
|---|---|
| Blender | 5.2+ (diuji di 5.4.0 Alpha, macOS) |
| Add-on | `bl_ext.blenderlab.mcp` dari *Get Extensions* (Blender Lab), aktif |
| Online access | Jalankan dengan `--online-mode`; autostart butuh `bpy.app.online_access` |
| Port | `127.0.0.1:9876` bebas saat Blender start |
| Python | 3.10+ di PATH (hanya untuk client dan doctor) |
| OS | macOS, Linux, Windows |

Jangan pernah pakai `--factory-startup`: extension mati dan command `blender_mcp`
menjadi tidak dikenal.

---

## Aturan keselamatan

1. **Kerja di sesi GUI user** (`bpy.app.background == False`).
2. **Jangan tutup atau kill Blender.** Kalau harus restart: simpan `.blend`, jelaskan
   alasannya, buka lagi file yang sama.
3. **Tanpa render kecuali owner meminta.** Bukti default berupa angka: posisi vertex,
   lebar, luas face, cakupan weight.
4. **Arahkan viewport ke elemen yang diedit** (`view3d.view_axis` + `view_selected`).
5. **Verifikasi di evaluated mesh**, bukan mesh sumber.
6. **Satu langkah atomik per panggilan MCP**, idempoten, mengembalikan metriknya.
7. **Simpan bertahap**, output di folder project.

Kebijakan render lengkap (termasuk nama engine Blender 5.4: `BLENDER_EEVEE`, bukan
`BLENDER_EEVEE_NEXT`, dan fakta scene glTF tidak punya kamera/lampu) ada di
`docs/RENDERING.md`.

---

## Cara kerja

```text
agent  ──TCP 127.0.0.1:9876──►  add-on MCP di dalam Blender  ──►  exec(python)
        JSON + "\0"             bpy / scene / depsgraph          mengisi `result`
```

- Request: `{"type":"execute","code":"...","strict_json":true}` + byte null.
- Reply: `{"status":"ok","result":{...}}` atau `{"status":"error","message":"<traceback>"}`.
- Snippet wajib mengisi `result` berupa dict yang JSON-serializable.
- Exception tidak mematikan sesi.

Detail protokol, batasan sandbox, dan helper fokus viewport: `docs/MCP_BRIDGE.md`.

---

## Studi kasus: rig tang crimping

glTF 16 MB di-rig live tanpa render:

| Metrik | Hasil |
|---|---|
| Mesh setelah weld + cut | 606 verts, 892 polys, 3 shell, 0 non-manifold |
| Rig | `root` kontrol, `arm_L` / `arm_R` deform, pairing diagonal |
| Engsel | pivot `(0, -0.26792, 0.02)`, sumbu world Y, ±4° per arm |
| Kontrol | custom property `open` 0–1 menggerakkan kedua bone |
| Deviasi rest | `2e-7` |
| Loop seam (frame 60 vs 1) | `0.0` |
| Rasio luas face buka/tutup | `0.999–1.0005` |
| Lebar handle | `0.2869 → 0.3569` |
| Lebar jaw | `0.1738 → 0.1895` |
| GLB hasil export | 1 mesh / 3 primitive, 1 skin / 3 joint, animasi 1–60, 9 tekstur |

Alasan pairing diagonal: split midline membuat jaw menutup saat handle membuka.
Detail lengkap: `docs/CASE_STUDY_CRIMPING.md` dan `docs/RIGGING_PLAYBOOK.md`.

Studi kasus kedua: avatar Roblox R15 plus walk loop (15 mesh tubuh, 17 tulang, IK
dua-tulang, gate kontak tanah dan jebakan FBX): `docs/CASE_STUDY_KNIGHT.md`.

Pemeriksaan tanpa render: `scripts/action_compat.py` (slot action Blender 5.x) dan
`scripts/glb_qa.py` (gate GLB murni stdlib, exit 1 kalau gagal).

---

## Struktur repo

```text
blender-mcp/
├── AGENTS.md                 setup + guardrails untuk agent
├── README.md / README.id.md  Inggris / Indonesia
├── docs/                     install, bridge, rigging, verifikasi, render, FAQ
├── scripts/                  installer, doctor, validator
├── skills/blender-live-rigging/
└── examples/crimping-tool/
```

---

## Agent yang didukung

| Agent | Target install |
|---|---|
| OpenCode | `~/.config/opencode/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex / Gemini CLI / Copilot / Cursor | `~/.agents/skills/` |
| Cursor | `~/.cursor/skills/` |

`--agent all` memasang ke semuanya. Untuk per project: `--scope project --project DIR`.
Windows memakai copy mode secara default.

---

## Kontribusi

Issue dan PR terbuka, termasuk skill baru, perbaikan OS lain, dan dokumentasi.

- Baca `CONTRIBUTING.md` untuk alur dan checklist PR.
- Jalankan `make check` sebelum push.
- Bug report: sertakan output `python3 scripts/doctor.py --json`.
- Keamanan: jangan buka issue publik; ikuti `SECURITY.md`.

Kalau menambah skill pihak ketiga, catat repo + commit hash di `docs/ECOSYSTEM.md`;
jangan vendor kode tanpa cek lisensi.

---

## Lisensi

MIT © 2026 Andy Pratama. Lihat `LICENSE`.
