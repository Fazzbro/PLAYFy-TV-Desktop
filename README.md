# PLAYFy TV Desktop Core

Clean-room implementation, protocol research suite, and native desktop application for sports streaming architecture and payload decryption analysis.

---

## Educational Purpose and Legal Research Notice

> [!WARNING]
> This repository and all associated source code are published strictly for educational purposes, security analysis, network protocol research, and clean-room interoperability research in accordance with applicable reverse-engineering and interoperability exceptions (such as 17 U.S.C. Section 1201(f)).
>
> 1. This software does not host, store, broadcast, or transmit any audio or video content. All media descriptors and stream locators are processed dynamically from external endpoints or user input.
> 2. The project demonstrates how modern streaming applications structure remote catalogs, derive dynamic decryption keys, and resolve adaptive bitrate protocols (HLS and MPEG-DASH).
> 3. Users and developers are solely responsible for ensuring compliance with all local laws, copyright regulations, and third-party terms of service when executing or testing this software.
> 4. The authors and maintainers assume no liability for misuse, unauthorized rebroadcasting, or damages resulting from the use of this codebase.

---

## Project Overview

PLAYFy TV Desktop Core is a fully independent, clean-room reimplementation of the client architecture recovered from the PLAYFy TV Android ecosystem. It replaces the legacy mobile client with a high-performance Windows desktop application and local backend service.

Key Capabilities:

- Clean-Room Crypto Pipeline: Fully decoded AES-CBC 128/256 payload decryption algorithm with custom signature tables, alphabet permutation, and initialization vector handling.
- Embed Stream Sniffing Engine: Five-phase extraction heuristic recovering HLS (.m3u8) and MPEG-DASH (.mpd) streams from dynamic JavaScript call sites, Base64 buffers, JSON configurations, and nested iframes.
- ClearKey DRM Resolution: Automatic extraction of ClearKey licensing keys and initialization of encrypted MPEG-DASH playback via Shaka Player.
- Live Goal Standings and Match Minute Engine: Real-time goal scorelines on match cards with authentic playing minutes (1'-45', stoppage time, half-time, 46'-90', full-time, and cricket overs).
- Multi-Server Redundancy: Seamless server switching across multiple broadcast links with automated proxy fallbacks.
- Pure Obsidian Interface: Built with React, TypeScript, Tailwind CSS, and Motion Primitives, following a strict monochrome visual hierarchy.
- Standalone Windows Binary: Self-contained desktop application compiled with PyInstaller and running against Microsoft Edge WebView2.

---

## System Architecture

The project is structured into modular layers separating protocol handling, backend orchestration, desktop shell hosting, and client rendering:

```
PLAYFy-TV-Desktop/
|-- desktop_app.py                Desktop application entry point (PyWebView + Edge WebView2)
|-- server.py                     Core backend service (FastAPI + CORS Proxy + Stream Sniffer)
|-- PLAYFy-TV-Desktop.spec        PyInstaller packaging specification
|-- requirements.txt              Python runtime dependencies
|-- logo.ico / logo.png           Embedded application branding and window icons
|-- windows_app/                  Native protocol and logic modules
|   |-- api_client.py             Remote Config client, CDN queries, and payload decryption
|   |-- crypto.py                 AES-CBC decryption engine with custom alphabet substitution
|   |-- score_engine.py           Parallel multi-league live score and match minute engine
|   |-- m3u_parser.py             M3U / M3U8 playlist parser and channel organizer
|   `-- database.py               Local favorites and watch history storage
|-- react_app/                    Production frontend application
|   |-- src/                      React 19, TypeScript, and Motion Primitives components
|   |-- dist/                     Pre-compiled production web bundle
|   `-- package.json              Frontend build configurations
`-- tools/                        Reverse engineering analysis scripts and protocol decoders
    |-- decrypt_all_endpoints.py  Automated payload decryption verification
    |-- disassemble_jni.py        Native disassembly analysis tools
    `-- test_bf.py                Crypto verification harnesses
```

---

## Technical Specifications and Findings

### 1. Cryptographic Schema

The remote provider distributes catalogs in encrypted form using AES in CBC mode with dynamic alphabet substitution:

- Base Catalog: `https://vorasp.online/`
- Target Files: `app.json`, `cc.json`, `cats/live-events.json`, `cats/sports.json`
- Alphabet Transformation:
  `zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP`
- Signature Table: Default signature `playfy_v1` maps through a 16-byte key derivation function with an 8-byte initial block and MD5 verification.

### 2. Stream Resolution Algorithm

Channel formats and live matches resolve stream URLs through a two-step process:

1. Direct Backlink Extraction:
   `https://vorasp.online/channels/{channel_id}.json`
   Yields individual broadcast server entries, headers, and ClearKey DRM credentials.
2. Web Sniffing Interceptor:
   If a server entry provides an embed webLink (`/embed.php?url=...` or external player), the backend sniffer navigates the DOM structure, decoding nested JavaScript configurations (`.loadSource()`, `player.src()`, Base64 buffers) to extract raw direct stream manifests.

### 3. Match Priority and Sub-Filtering

The client organizes sports matches using a 3-level priority sort order:

1. State Priority: `LIVE` (Priority 2) > `STARTING_SOON` / `UPCOMING` (Priority 1) > `ENDED` (Priority 0).
2. Pinned Status: Pinned matches take precedence within their respective state.
3. Start Time: Earliest kickoff time first.

---

## Installation and Setup

### Prerequisites

- Windows 10 or Windows 11 (64-bit)
- Python 3.10 or higher
- Microsoft Edge WebView2 Runtime (pre-installed on Windows 10/11)
- Node.js 18 or higher (only required if rebuilding the frontend)

### Quick Start (Development Mode)

1. Clone the repository:
   ```cmd
   git clone https://github.com/Fazzbro/PLAYFy-TV-Desktop.git
   cd PLAYFy-TV-Desktop
   ```

2. Create and activate a Python virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

4. Launch the application:
   ```cmd
   python desktop_app.py
   ```

The application automatically starts the local core engine on `http://127.0.0.1:8000` and opens the native desktop window.

### Running the Web Server Independently

To run only the local streaming and API backend:
```cmd
python server.py
```
Access the web client at `http://localhost:8000` from any browser.

---

## Building the Standalone Executable

To compile the standalone Windows `.exe` without requiring Python to be installed on target machines:

1. Build the React frontend (optional if using tracked `react_app/dist`):
   ```cmd
   cd react_app
   npm install
   npm run build
   cd ..
   ```

2. Compile using PyInstaller:
   ```cmd
   pyinstaller PLAYFy-TV-Desktop.spec --noconfirm
   ```

The compiled standalone executable and runtime assets are generated in:
`dist\PLAYFy-TV\PLAYFy-TV.exe`

---

## Developer Support and Contributing

We welcome community contributions, bug reports, and pull requests from protocol researchers and developers.

### Issue Reporting Guidelines

- Use the GitHub Issue Tracker to report bugs, crashes, or stream parser regressions.
- Include OS version, Python version, error tracebacks from the console, and exact match or channel titles when reporting stream loading issues.
- Do not paste raw copyrighted stream URLs in public issues; refer to channel IDs or server indices instead.

### Adding New Features or Scrapers

1. Fork the repository and create a descriptive feature branch:
   ```cmd
   git checkout -b feature/improved-hls-parser
   ```
2. Ensure strict architectural separation:
   - Network extraction code belongs in `windows_app/` or `tools/`.
   - Backend routes and stream sniffing heuristics belong in `server.py`.
   - UI components belong in `react_app/src/components/`.
3. Adhere to the code style:
   - Type annotations for all Python and TypeScript functions.
   - Clean obsidian black and white aesthetic for all UI components.
   - Strict rule: No emojis in source files, commit messages, or documentation.
4. Run test suites before submitting pull requests:
   ```cmd
   python -m unittest discover -s windows_app
   ```
5. Submit a pull request detailing the changes and verification steps.

### Technical Discussions and Support

For architecture questions, reverse engineering methodologies, and developer inquiries:
- GitHub Discussions: Use the Discussions tab on this repository.
- Security Disclosures: For responsible disclosure of security vulnerabilities, contact via GitHub security advisories.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
All product names, logos, and brands are property of their respective owners.
