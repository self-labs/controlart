# ControlArt for Home Assistant: Repository Conventions (for AI agents)

Custom Home Assistant integration (domain `controlart`) for the **ControlArt wired modules**
configured through mdConfig: the **relay** module (10 relay outputs, 12 inputs) and the **dimmer**
module (channels with a 0 to 255 level, 12 inputs). It talks to each module over TCP on the LAN
(port 4998 by default), local push, no cloud. Installed through HACS as a custom repository.

**Independent project since 2026-10-18.** It started as a fork of
[tompsonpecini/controlart](https://github.com/tompsonpecini/controlart) (MIT); the credit stays in
the README and his copyright line stays in `LICENSE` (the MIT license requires it). There is no
contribution flow back anymore: the `upstream` remote is kept only to read his fixes, with
`tagOpt --no-tags` so his `v1.x` tags never mix with ours. Bringing a fix from him is a
`cherry-pick` that keeps him as the commit author.

ControlArt is **not** being phased out: each Self-Labs client picks the hardware they want to pay
for (ControlArt or KinCony), so new installs can still use these modules. The installer's
guide (pt-BR) lives in the private repo `cateim/homeassistant`, `docs/controlart.md`; client data
never comes here.

## Structure

- `custom_components/controlart/`: the integration.
  - `protocolo.py`: TCP connection per module (`ModuloConexao`), frame parsing (`setcmd` relay,
    `setdmmd` dimmer), command confirmation (3 s), `getmd` watchdog (10 s), dimmer ramps, the
    keypad second-press polling.
  - `config_flow.py`: setup by IP only; the module reports MAC and type when probed.
  - `registro.py`: removes entities the config no longer produces, writes the firmware into the
    device.
  - `light.py`, `event.py`, `binary_sensor.py`, `sensor.py` (IP), `button.py` (all on / all off),
    `diagnostics.py`, `entidade.py` (shared `DeviceInfo`).
  - `strings.json` + `translations/{en,pt-BR}.json`: keep the three in sync
    (`tests/test_traducoes.py` checks the keys the lights use, not all of them).
  - `brand/`: integration icon and logo, light and `dark_` variants, cut from ControlArt's
    official horizontal logo (`Logo_Horizontal_semFundo_Site_Alta.png` on controlart.com.br).
    The dark set keeps the site's colours (teal ring, white disc and text); the light set
    takes the favicon's (grey ring `#6E6A6C`, teal disc `#5B9A97`, grey text). Icon 256 and
    512 square, logo 128 and 256 high, transparent, trimmed.
- `tests/`: stdlib `unittest` with a fake Home Assistant (`tests/ha_falso.py`). No pytest, no HA
  install.
- `docs/protocolo.md`: the module protocol and the traps found on real hardware.
- `README.md`: the user manual, in pt-BR, with an English summary at the end.
- `CHANGELOG.md`: Keep a Changelog 1.1.0, pt-BR.

## Commands

```powershell
python -B -m unittest discover -s tests
```

CI (`.github/workflows/validar.yml`) runs `hassfest`, `hacs/action` and the tests on every push to
`master`. The HACS check needs issues enabled and topics set on the GitHub repository.

## Conventions

- **Code comments and log messages are pt-BR without accents** (the existing style of every `.py`
  file). The README, `docs/` and the changelog use pt-BR with full accentuation.
- Entity `unique_id`s are `controlart_<mac>_<kind>` where `<mac>` is the three bytes the module
  reports (e.g. `4E-50-D2`). Never change that pattern: it would recreate every entity in the
  installed houses.
- **The MAC stays on the device card.** The three bytes the module reports go into `connections`
  as `CONNECTION_NETWORK_MAC`, so the card shows them, the same as in mdConfig. Maintainer's
  decision (2026-10-18): Tompson's 1.1.0 removed it, 2026.10.1 shipped that by mistake and
  2026.10.2 restored it. Never remove it again.
- Real firmware replies with just the number (`3027` relay, `1021` dimmer); MAC replies are
  `macaddr_RT,<mac>` on the relay and `macaddr,<mac>` on the dimmer.
- Never commit IPs or MACs of a client. `legado.py` is git-ignored for that reason.
- No em dashes or en dashes anywhere.

## Versioning and releases

CalVer `YYYY.M.R` in `manifest.json`, matching the annotated git tag `vYYYY.M.R` and a GitHub
release whose notes are the changelog section. HACS offers releases as updates once they exist.
`1.0.0` and `1.0.1` are Tompson's versions and keep their tags.

Release order: close `[Unreleased]` in `CHANGELOG.md` into `## [X] - YYYY-MM-DD`, update the
footer links, bump `manifest.json`, commit, then tag and release in the same push. Only with the
maintainer's explicit go-ahead.

## Git

- Default branch `master`.
- Commits: short imperative subject in pt-BR (the history's style), body explaining the why.
- **Never commit, push, tag or release without the maintainer explicitly asking**, one approval per
  operation.
