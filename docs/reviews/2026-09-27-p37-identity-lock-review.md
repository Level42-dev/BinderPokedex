# P37: Identity-Lock-Kandidat A zur Bildentscheidung

Stand: 27.09.2026. **Technisch und in den Einlegern geprüft, aber noch keine Nutzerfreigabe, Promotion oder PDF-Aktivierung.** Kandidat `p37-il-20260927-a` ist der isolierte Fallback für `ME03`.

## Reproduzierbare Eingaben und Rückgaben

- Unveränderlicher Szenenjob SHA-256 `00b76b9cf727c031340376ced80caba0f89347968af8de7b2d2870627b5dc0f6`; 300-dpi-Upscale-Job SHA-256 `32840ce7155c524247b15dd9f5140182bf11b09d07afe5c2b9808c9f10202d9c`.
- Beide Jobs wurden vor GPU-Ausführung hashvalidiert. `run.json`, `comfyui.log` und jeweils genau ein Ausgabebild sind vollständig zurückgeholt; Run-Hashes `d0d473967445ef00a632ee530b2be28d51f6661221bd898796fafdfdd22fc72d` und `98a0dec789d57f21b673b3eae15d01a8c6dfe6248f22a5eae95e9eb7f47289d1`. Gerät MPS und Ausgabedateihashes sind bestätigt.
- Rohbild SHA-256 `20e88678fdbd21b074975e76f2c2352b8877a65f90001e5e8d13291862ffb523`: 54.082 vollständig opake Quellpixel geprüft, 0 verändert. Druckmaster 2368 × 3268 px SHA-256 `fc1df7acd8359153d53eabbaf23c22a189dbc8d694e58ed5cd8a7c3b683e7b76`; deutsche Vorschau SHA-256 `e15af85aec4c7ec991ffec414d29585161ec5580417153ac2e92cd96dfc4663f`. Alle neun physischen 750 × 1050-px-Karten liegen im ignorierten Kandidatenverzeichnis und wurden als Karte sowie im Gesamtbogen geprüft.

## Bildvergleich und offener Eindruck

Serpifeu (r3c1), Bauz (r3c2) und Mega-Zygarde (r3c3) entsprechen ihren exakten Official-Artwork-Quellen. Anders als in den abgelehnten B/C/D-One-shots ist Zygardes linkes violettes Emblem vollständig innerhalb von r3c3; auch Hände, rechter Kanonenrand und untere Ausläufer werden nicht abgeschnitten. Das deutsche Setlogo ist vorhanden. Die Landschaft bleibt über alle neun Karten kontinuierlich, ohne die bei P16 sichtbare gerade Unterkanten-Naht.

Der Bildstil ist allerdings flächig und ruhig; bei Serpifeu und Bauz sind Kontaktschatten nur schwach, Mega-Zygarde schwebt gemäß seiner Quellpose ohne deutliche Projektion. Diese bekannte Einschränkung wurde dem Nutzer mit Gesamtbild und allen drei beschrifteten Einleger-Quellbild-Paaren ausdrücklich zur visuellen Entscheidung vorgelegt. Technische Pixelgleichheit wird nicht als Bildfreigabe ausgegeben. Bis zur Antwort bleiben Manifest, Master, `pdf.enabled` und PDF unverändert.

Der aktive ME03-Master und die bestehende deutsche PDF behalten ihre Ausgangshashes `f168f308c04d3cfd617d49378ae74ebc3bb5ad9ccb6fb6fbc8e1f01dcd1a065f` und `7adc6723a3b8862c515208fbc8cade0559f2cd19e9dc93c28cba525b3d10ad95`.
