#!/usr/bin/env python3
"""Build printable technician briefs (PT-BR + EN) as PDF.

Renders a self-contained HTML file with the U26 board photos embedded, then
uses Microsoft Edge headless to print it to PDF. No extra Python packages.

Output (in 09_builds/recovery_stock_1mb/):
  RP500_reflash_brief_PT-BR.pdf
  RP500_reflash_brief_EN.pdf
"""
import base64
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "05_evidence", "board")
OUT = os.path.join(ROOT, "09_builds", "recovery_stock_1mb")
# Optional downscaled copies (keeps the PDF small); falls back to the originals.
BRIEF_IMG = os.environ.get(
    "RP500_BRIEF_IMG",
    os.path.join(tempfile.gettempdir(), "opencode", "rp500_brief"),
)

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

CSS = """
@page { size: A4; margin: 15mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; line-height: 1.42; color: #111; }
h1 { font-size: 19pt; margin: 0 0 1mm; color: #111; }
.sub { color: #555; font-size: 10pt; margin: 0 0 5mm; }
h2 { font-size: 12.5pt; margin: 6mm 0 2mm; border-bottom: 1.6px solid #b00; padding-bottom: 1mm; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 4mm; font-size: 9pt; }
th, td { border: 1px solid #999; padding: 1.6mm 2mm; text-align: left; vertical-align: top; }
th { background: #eee; }
.warn { border: 2px solid #b00; background: #fff2f2; padding: 3mm 4mm; margin: 2mm 0 5mm; page-break-inside: avoid; }
.warn b { color: #b00; }
.warn ul { margin: 1mm 0 0 4mm; padding: 0; }
.mono { font-family: Consolas, "Courier New", monospace; font-size: 8.6pt; }
pre { background: #f4f4f4; border: 1px solid #ccc; padding: 2mm 3mm; font-family: Consolas, monospace; font-size: 8.6pt; margin: 1mm 0 3mm; white-space: pre-wrap; }
.small { font-size: 8.4pt; color: #444; }
.photos { display: flex; gap: 4mm; margin: 2mm 0 4mm; page-break-inside: avoid; }
.photos figure { flex: 1; margin: 0; }
.photos img { width: 100%; border: 1px solid #888; }
figcaption { font-size: 7.8pt; color: #444; margin-top: 1mm; }
ol, ul { margin: 1mm 0 3mm 5mm; padding: 0; }
li { margin: 1.1mm 0; }
.footer { margin-top: 6mm; border-top: 1px solid #bbb; padding-top: 2mm; font-size: 8pt; color: #555; }
.pagebreak { page-break-before: always; }
"""


def data_uri(name):
    small = os.path.join(BRIEF_IMG, name)
    path = small if os.path.exists(small) else os.path.join(BOARD, name)
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def photos_block(pt):
    close = data_uri("10_flash_SST29AL016J.jpg")
    full = data_uri("01_full_board_top.jpg")
    if pt:
        cap1 = "U26 — flash SST29AL016J (TSOP-48). O ponto do pino 1 é a referência."
        cap2 = "Vista geral da placa 80-0145-A: U26 fica entre o AudioDNA2 (U25), a SDRAM (U24) e os latches."
    else:
        cap1 = "U26 — SST29AL016J flash (TSOP-48). The pin-1 dot is the reference."
        cap2 = "Board 80-0145-A overview: U26 sits between the AudioDNA2 (U25), the SDRAM (U24) and the latches."
    return f"""
    <div class="photos">
      <figure><img src="{close}"><figcaption>{cap1}</figcaption></figure>
      <figure><img src="{full}"><figcaption>{cap2}</figcaption></figure>
    </div>
    """


def html_pt():
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><style>{CSS}</style></head><body>

<h1>RP500 — Regravação do firmware</h1>
<p class="sub">Briefing para o técnico · DigiTech RP500 · placa <b>80-0145-A</b> · 2026-11-12</p>

<div class="warn">
<b>Leia antes de começar</b>
<ul>
<li><b>Tensão: 3,3 V. Nunca 5 V.</b></li>
<li><b>Não</b> mexa no <b>U19 (TAS1020B)</b> nem na EEPROM I²C dele — é o controlador USB, não faz parte do reparo.</li>
<li><b>Não</b> ligue o aparelho com o <b>U26</b> removido.</li>
<li>O único chip a regravar é o <b>U26</b>. Nada mais na placa precisa ser alterado.</li>
</ul>
</div>

<h2>1. O chip</h2>
<table>
<tr><th>Item</th><th>Valor</th></tr>
<tr><td>Placa</td><td>DigiTech RP500, <b>80-0145-A</b>, lado dos componentes</td></tr>
<tr><td>Referência</td><td><b>U26</b></td></tr>
<tr><td>Part number (sob a etiqueta branca)</td><td><b class="mono">SST29AL016J70TFI02</b> (Spansion / SST)</td></tr>
<tr><td>Encapsulamento</td><td><b>TSOP-48, pitch de 0,5 mm</b></td></tr>
<tr><td>Tamanho</td><td><b>16 Mbit = 2 MB</b> (modo byte, 2M × 8)</td></tr>
<tr><td>Alimentação</td><td><b>3,0–3,6 V (3,3 V)</b> — <b>nunca 5 V</b></td></tr>
<tr><td>Velocidade</td><td>70 ns</td></tr>
<tr><td>Etiqueta de fábrica</td><td><span class="mono">72-0089-12&nbsp;&nbsp;V1.20&nbsp;&nbsp;RP500&nbsp;&nbsp;CS.8CD9</span></td></tr>
</table>
<p>O chip fica entre o <b>AudioDNA2</b> (QFP grande, U25), a <b>SDRAM Samsung K4S641632N</b> (U24) e a fileira de <b>latches 74HCT574</b>.</p>
{photos_block(True)}

<h2>2. O que o técnico precisa</h2>
<table>
<tr><th>Item</th><th>Requisito</th></tr>
<tr><td>Gravador</td><td><b>XGecu T48</b> (recomendado) ou <b>TL866II Plus</b> com <span class="mono">SST29AL016J</span> / <span class="mono">SST29AL016</span> na lista de dispositivos</td></tr>
<tr><td>Adaptador</td><td><b>TSOP48 para DIP48, pitch de 0,5 mm</b> (não é TSOP56)</td></tr>
<tr><td>Tensão</td><td><b>3,3 V</b> (ajustar o gravador/adaptador para 3,3 V, não 5 V)</td></tr>
<tr><td>Ferramentas</td><td>Estação de ar quente, fluxo, pasta de solda ou ferro fino, fita Kapton, lupa</td></tr>
<tr><td>Software</td><td>O software do próprio gravador; não precisa de ferramenta especial</td></tr>
</table>
<p>Se a lista do gravador não tiver <span class="mono">SST29AL016J</span>, use a entrada <b class="mono">SST29AL016</b> (mesma família JEDEC) ou um gravador que liste a Spansion <span class="mono">S29AL016J</span>.</p>

<h2>3. Os arquivos de imagem</h2>
<p>Os dois arquivos <span class="mono">.bin</span> devem ser entregues <b>junto com este PDF</b> (origem: <span class="mono">09_builds/recovery_stock_1mb/</span>):</p>
<table>
<tr><th>Arquivo</th><th>Tamanho</th><th>SHA-256</th></tr>
<tr><td class="mono">stock_1mb.bin</td><td>1.048.576</td><td class="mono" style="font-size:7.4pt">718fda7de9206838d5e4945d7cff0c890c3573dc68c81142df23f7dab765fa11</td></tr>
<tr><td class="mono">stock_2mb_padded_ff.bin</td><td>2.097.152</td><td class="mono" style="font-size:7.4pt">01978cbfbe20fc565a3c8100b415798855fd90e6bb6580ad193f5df5ac507d8d</td></tr>
</table>
<ul>
<li><span class="mono">stock_1mb.bin</span> é o firmware do RP500, bruto, <b>1 MB</b>.</li>
<li><span class="mono">stock_2mb_padded_ff.bin</span> é o mesmo 1 MB seguido de <b>1 MB de <span class="mono">0xFF</span></b>, para gravadores que exigem o tamanho total de 2 MB.</li>
<li><b>Não</b> use nenhum arquivo <span class="mono">.DigBin</span> diretamente; o gravador precisa do <span class="mono">.bin</span> bruto acima.</li>
</ul>
<p>Primeiros 16 bytes do firmware (para conferência):</p>
<pre>EA 00 02 00 6B 53 91 DF 32 00 FF 02 23 4E 01 1F</pre>
<p>Conferência do hash no Windows:</p>
<pre>certutil -hashfile stock_1mb.bin SHA256</pre>

<h2>4. Procedimento</h2>
<ol>
<li><b>Fotografe o U26 e anote o pino 1</b> antes de remover. O pino 1 é o pequeno ponto circular no encapsulamento; a placa tem uma marca branca de canto.</li>
<li><b>Dessolde o U26</b> com ar quente. Proteja a SDRAM, o DSP e os latches vizinhos com fita Kapton. Não levante as ilhas (pads).</li>
<li>Limpe as ilhas e coloque o U26 no <b>adaptador TSOP48 0,5 mm</b>.</li>
<li><b>Leia o chip original por completo (2 MB)</b> e salve como backup (<span class="mono">orig_2mb.bin</span>). Confira os primeiros 16 bytes com a lista acima; o original pode ser a imagem 2.0 de fábrica ou a 2.2 que falhou.</li>
<li><b>Apague</b> o chip.</li>
<li><b>Grave</b> uma das opções:
  <ul>
  <li><span class="mono">stock_1mb.bin</span> no endereço <b class="mono">0x000000</b>, ou</li>
  <li><span class="mono">stock_2mb_padded_ff.bin</span> no endereço <b class="mono">0x000000</b>, se o gravador exigir o arquivo de 2 MB completo.</li>
  </ul>
</li>
<li><b>Verifique</b> toda a área gravada.</li>
<li><b>Recoloque o U26</b> na orientação original (ponto do pino 1 alinhado com a marca da placa).</li>
<li>Ligue. O aparelho deve inicializar o firmware original e o display deve mostrar a inicialização normal do RP500; o USB deve enumerar como <b class="mono">VID_1210 / PID_0016</b> (DigiTech RP500).</li>
</ol>

<h2>5. Sobre o 1 MB superior</h2>
<p>O updater do RP500 endereça apenas <b>16 × 64 KB = 1 MB</b>, então o firmware fica na <b>primeira metade</b> do chip de 2 MB. O 1 MB superior está fora do mapa do updater.</p>
<ul>
<li>Se o 1 MB superior original estiver <b>todo <span class="mono">0xFF</span></b>, o arquivo preenchido está correto.</li>
<li>Se o 1 MB superior original tiver dados, <b>não sobrescreva</b>: grave o 1 MB original na metade inferior e restaure a metade superior original (mescle <span class="mono">stock_1mb.bin</span> + <span class="mono">orig_2mb.bin[0x100000:0x200000]</span>).</li>
</ul>

<h2>6. Não faça</h2>
<ul>
<li><b>Não</b> use tensão de 5 V.</li>
<li><b>Não</b> mexa no <b>U19 (TAS1020B)</b> nem na pequena EEPROM I²C dele. É o controlador USB e não faz parte deste reparo.</li>
<li><b>Não</b> grave a imagem 2.2 S3b que falhou (<span class="mono">be9676…</span>).</li>
<li><b>Não</b> ligue o aparelho com o U26 removido.</li>
</ul>

<h2>7. Como saber que deu certo</h2>
<ul>
<li>Display: inicialização normal do RP500, sem desligar em seguida.</li>
<li>USB: <b class="mono">VID_1210 / PID_0016</b>.</li>
<li>O aparelho aceita o firmware 2.0 original e funciona normalmente.</li>
</ul>
<p>Se não inicializar, confira o pino 1, as soldas e o resultado da verificação antes de mexer em qualquer outra coisa.</p>

<h2>8. Custo realista</h2>
<p>O único item especial é o <b>adaptador TSOP48 0,5 mm</b>. Qualquer oficina que faz BIOS/EC/firmware embarcado já tem um T48 ou TL866 e o adaptador; o serviço em si leva 15–30 minutos. Se não tiverem o adaptador, essa é a única compra — e ainda é muito mais barato do que uma placa nova ou um chip pré-gravado.</p>

<div class="footer">Gerado a partir de <span class="mono">09_builds/recovery_stock_1mb/BRIEF_TECNICO_pt-BR.md</span> · projeto RP500 · 2026-11-12 · este documento descreve apenas a regravação do U26.</div>

</body></html>"""


def html_en():
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>{CSS}</style></head><body>

<h1>RP500 — firmware reflash</h1>
<p class="sub">Technician brief · DigiTech RP500 · board <b>80-0145-A</b> · 2026-11-12</p>

<div class="warn">
<b>Read before you start</b>
<ul>
<li><b>Voltage: 3.3 V. Never 5 V.</b></li>
<li><b>Do not</b> touch <b>U19 (TAS1020B)</b> or its I²C EEPROM — that is the USB controller and is not part of this repair.</li>
<li><b>Do not</b> power the unit with <b>U26</b> removed.</li>
<li>The only chip to reflash is <b>U26</b>. Nothing else on the board needs to change.</li>
</ul>
</div>

<h2>1. The chip</h2>
<table>
<tr><th>Item</th><th>Value</th></tr>
<tr><td>Board</td><td>DigiTech RP500, <b>80-0145-A</b>, component side</td></tr>
<tr><td>Reference</td><td><b>U26</b></td></tr>
<tr><td>Part number (under the white label)</td><td><b class="mono">SST29AL016J70TFI02</b> (Spansion / SST)</td></tr>
<tr><td>Package</td><td><b>TSOP-48, 0.5 mm pitch</b></td></tr>
<tr><td>Size</td><td><b>16 Mbit = 2 MB</b> (byte mode, 2M × 8)</td></tr>
<tr><td>Supply</td><td><b>3.0–3.6 V (3.3 V)</b> — <b>never 5 V</b></td></tr>
<tr><td>Speed</td><td>70 ns</td></tr>
<tr><td>Factory label</td><td><span class="mono">72-0089-12&nbsp;&nbsp;V1.20&nbsp;&nbsp;RP500&nbsp;&nbsp;CS.8CD9</span></td></tr>
</table>
<p>The chip sits between the <b>AudioDNA2</b> (large QFP, U25), the <b>Samsung K4S641632N</b> SDRAM (U24) and the row of <b>74HCT574</b> latches.</p>
{photos_block(False)}

<h2>2. What the technician needs</h2>
<table>
<tr><th>Item</th><th>Requirement</th></tr>
<tr><td>Programmer</td><td><b>XGecu T48</b> (recommended) or <b>TL866II Plus</b> with <span class="mono">SST29AL016J</span> / <span class="mono">SST29AL016</span> in its device list</td></tr>
<tr><td>Adapter</td><td><b>TSOP48 to DIP48, 0.5 mm pitch</b> (not TSOP56)</td></tr>
<tr><td>Voltage</td><td><b>3.3 V</b> (set the programmer/adapter to 3.3 V, not 5 V)</td></tr>
<tr><td>Tools</td><td>Hot-air station, flux, solder paste or fine iron, Kapton tape, magnifier</td></tr>
<tr><td>Software</td><td>The programmer's own software; no special tool needed</td></tr>
</table>
<p>If the programmer's list has no <span class="mono">SST29AL016J</span>, use the <b class="mono">SST29AL016</b> entry (same JEDEC family) or a programmer that lists the Spansion <span class="mono">S29AL016J</span>.</p>

<h2>3. The image files</h2>
<p>The two <span class="mono">.bin</span> files must be supplied <b>alongside this PDF</b> (source: <span class="mono">09_builds/recovery_stock_1mb/</span>):</p>
<table>
<tr><th>File</th><th>Size</th><th>SHA-256</th></tr>
<tr><td class="mono">stock_1mb.bin</td><td>1,048,576</td><td class="mono" style="font-size:7.4pt">718fda7de9206838d5e4945d7cff0c890c3573dc68c81142df23f7dab765fa11</td></tr>
<tr><td class="mono">stock_2mb_padded_ff.bin</td><td>2,097,152</td><td class="mono" style="font-size:7.4pt">01978cbfbe20fc565a3c8100b415798855fd90e6bb6580ad193f5df5ac507d8d</td></tr>
</table>
<ul>
<li><span class="mono">stock_1mb.bin</span> is the RP500 firmware, raw, <b>1 MB</b>.</li>
<li><span class="mono">stock_2mb_padded_ff.bin</span> is the same 1 MB followed by <b>1 MB of <span class="mono">0xFF</span></b>, for programmers that insist on the chip's full 2 MB size.</li>
<li><b>Do not</b> use any <span class="mono">.DigBin</span> file directly; the programmer needs the raw <span class="mono">.bin</span> above.</li>
</ul>
<p>First 16 bytes of the firmware (for checking):</p>
<pre>EA 00 02 00 6B 53 91 DF 32 00 FF 02 23 4E 01 1F</pre>
<p>Windows hash check:</p>
<pre>certutil -hashfile stock_1mb.bin SHA256</pre>

<h2>4. Procedure</h2>
<ol>
<li><b>Photograph U26 and note pin 1</b> before removal. Pin 1 is the small circular dot on the package; the board has a white corner marker.</li>
<li><b>Desolder U26</b> with hot air. Protect the neighbouring SDRAM, DSP and latches with Kapton tape. Do not lift pads.</li>
<li>Clean the pads and place U26 in the <b>TSOP48 0.5 mm adapter</b>.</li>
<li><b>Read the original chip completely (2 MB)</b> and save it as a backup (<span class="mono">orig_2mb.bin</span>). Check the first 16 bytes against the list above; the original may be the stock 2.0 image or the failed 2.2 image.</li>
<li><b>Erase</b> the chip.</li>
<li><b>Program</b> one of:
  <ul>
  <li><span class="mono">stock_1mb.bin</span> at address <b class="mono">0x000000</b>, or</li>
  <li><span class="mono">stock_2mb_padded_ff.bin</span> at address <b class="mono">0x000000</b> if the programmer requires a full 2 MB file.</li>
  </ul>
</li>
<li><b>Verify</b> the whole programmed area.</li>
<li><b>Reinstall U26</b> in the original orientation (pin-1 dot aligned with the board marker).</li>
<li>Power on. The unit should boot the stock firmware and the display should show the normal RP500 start-up; USB should enumerate as <b class="mono">VID_1210 / PID_0016</b> (DigiTech RP500).</li>
</ol>

<h2>5. About the upper 1 MB</h2>
<p>The RP500 updater addresses only <b>16 × 64 KB = 1 MB</b>, so the firmware lives in the <b>first half</b> of the 2 MB chip. The upper 1 MB is outside the updater's map.</p>
<ul>
<li>If the original upper 1 MB reads <b>all <span class="mono">0xFF</span></b>, the padded file is correct.</li>
<li>If the original upper 1 MB contains data, <b>do not overwrite it</b>: program the stock 1 MB into the lower half and restore the original upper half (merge <span class="mono">stock_1mb.bin</span> + <span class="mono">orig_2mb.bin[0x100000:0x200000]</span>).</li>
</ul>

<h2>6. Do not</h2>
<ul>
<li><b>Do not</b> use a 5 V setting.</li>
<li><b>Do not</b> touch <b>U19 (TAS1020B)</b> or its small I²C EEPROM. That is the USB controller and is not part of this repair.</li>
<li><b>Do not</b> program the failed 2.2 S3b image (<span class="mono">be9676…</span>).</li>
<li><b>Do not</b> power the unit with U26 removed.</li>
</ul>

<h2>7. What "success" looks like</h2>
<ul>
<li>Display: normal RP500 boot, no immediate power-down.</li>
<li>USB: <b class="mono">VID_1210 / PID_0016</b>.</li>
<li>The unit accepts the stock 2.0 firmware and behaves normally.</li>
</ul>
<p>If it does not boot, re-check pin 1, solder joints, and the verify result before changing anything else.</p>

<h2>8. Realistic cost</h2>
<p>The only special item is the <b>TSOP48 0.5 mm adapter</b>. Any shop that does BIOS/EC/embedded-firmware work already has a T48 or TL866 and the adapter; the job itself takes 15–30 minutes. If they do not have the adapter, that is the only purchase — and it is still far cheaper than a new board or a pre-programmed chip.</p>

<div class="footer">Generated from <span class="mono">09_builds/recovery_stock_1mb/TECHNICIAN_BRIEF.md</span> · RP500 project · 2026-11-12 · this document covers only the U26 reflash.</div>

</body></html>"""


def find_edge():
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("No Edge/Chrome found in the usual locations.")


def render(html, stem, edge):
    tmp = os.path.join(tempfile.gettempdir(), "opencode", "rp500_brief")
    os.makedirs(tmp, exist_ok=True)
    html_path = os.path.join(tmp, stem + ".html")
    pdf_path = os.path.join(OUT, stem + ".pdf")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    uri = "file:///" + html_path.replace("\\", "/")
    udd = tempfile.mkdtemp(prefix="edgepdf_")
    cmd = [
        edge,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--user-data-dir={udd}",
        f"--print-to-pdf={pdf_path}",
        uri,
    ]
    subprocess.run(cmd, check=True)
    if not os.path.exists(pdf_path):
        raise SystemExit("Edge did not produce " + pdf_path)
    print(pdf_path, os.path.getsize(pdf_path), "bytes")


def main():
    edge = find_edge()
    render(html_pt(), "RP500_reflash_brief_PT-BR", edge)
    render(html_en(), "RP500_reflash_brief_EN", edge)


if __name__ == "__main__":
    main()
