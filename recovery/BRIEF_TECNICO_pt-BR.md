# RP500 — restauração do firmware (briefing para o técnico)

**Objetivo:** restaurar o firmware principal do RP500 regravando apenas um
chip de memória flash. Nada mais na placa precisa ser alterado.

---

## 1. O chip

| Item | Valor |
|---|---|
| Placa | DigiTech RP500, **80-0145-A**, lado dos componentes |
| Referência | **U26** |
| Part number (sob a etiqueta branca) | **`SST29AL016J70TFI02`** (Spansion / SST) |
| Encapsulamento | **TSOP-48, pitch de 0,5 mm** |
| Tamanho | **16 Mbit = 2 MB** (modo byte, 2M x 8) |
| Alimentação | **3,0–3,6 V (3,3 V)** — **nunca 5 V** |
| Velocidade | 70 ns |
| Etiqueta de fábrica | `72-0089-12  V1.20  RP500  CS.8CD9` |

O chip fica entre o **AudioDNA2** (QFP grande, U25), a **SDRAM Samsung
K4S641632N** (U24) e a fileira de **latches 74HCT574**.

Fotos: `05_evidence/board/10_flash_SST29AL016J.jpg`,
`05_evidence/board/08_dsp_sdram_flash_label.jpg`,
`05_evidence/board/01_full_board_top.jpg`.

---

## 2. O que o técnico precisa

| Item | Requisito |
|---|---|
| Gravador | **XGecu T48** (recomendado) ou **TL866II Plus** com `SST29AL016J` / `SST29AL016` na lista de dispositivos |
| Adaptador | **TSOP48 para DIP48, pitch de 0,5 mm** (não é TSOP56) |
| Tensão | **3,3 V** (ajustar o gravador/adaptador para 3,3 V, não 5 V) |
| Ferramentas | Estação de ar quente, fluxo, pasta de solda ou ferro fino, fita Kapton, lupa |
| Software | O software do próprio gravador; não precisa de ferramenta especial |

Se a lista do gravador não tiver `SST29AL016J`, use a entrada
**`SST29AL016`** (mesma família JEDEC) ou um gravador que liste a Spansion
`S29AL016J`.

---

## 3. Os arquivos de imagem

Todos em `D:\OPENCODE\RP500\09_builds\recovery_stock_1mb\`:

| Arquivo | Tamanho | SHA-256 |
|---|---|---|
| `stock_1mb.bin` | 1.048.576 | `718fda7de9206838d5e4945d7cff0c890c3573dc68c81142df23f7dab765fa11` |
| `stock_2mb_padded_ff.bin` | 2.097.152 | `01978cbfbe20fc565a3c8100b415798855fd90e6bb6580ad193f5df5ac507d8d` |

- `stock_1mb.bin` é o firmware do RP500, bruto, **1 MB**.
- `stock_2mb_padded_ff.bin` é o mesmo 1 MB seguido de **1 MB de `0xFF`**,
  para gravadores que exigem o tamanho total de 2 MB do chip.
- **Não** use nenhum arquivo `.DigBin` diretamente; o gravador precisa do
  `.bin` bruto acima.
- Os primeiros 16 bytes do firmware são:

```
EA 00 02 00 6B 53 91 DF 32 00 FF 02 23 4E 01 1F
```

- Conferência do hash no Windows:

```
certutil -hashfile stock_1mb.bin SHA256
```

---

## 4. Procedimento

1. **Fotografe o U26 e anote o pino 1** antes de remover. O pino 1 é o
   pequeno ponto circular no encapsulamento; a placa tem uma marca branca de
   canto.
2. **Dessolde o U26** com ar quente. Proteja a SDRAM, o DSP e os latches
   vizinhos com fita Kapton. Não levante as ilhas (pads).
3. Limpe as ilhas e coloque o U26 no **adaptador TSOP48 0,5 mm**.
4. **Leia o chip original por completo (2 MB)** e salve como backup
   (`orig_2mb.bin`). Confira os primeiros 16 bytes com a lista acima; o
   original pode ser a imagem 2.0 de fábrica ou a 2.2 que falhou.
5. **Apague** o chip.
6. **Grave** uma das opções:
   - `stock_1mb.bin` no endereço **`0x000000`**, ou
   - `stock_2mb_padded_ff.bin` no endereço **`0x000000`**, se o gravador
     exigir o arquivo de 2 MB completo.
7. **Verifique** toda a área gravada.
8. **Recoloque o U26** na orientação original (ponto do pino 1 alinhado com
   a marca da placa).
9. Ligue. O aparelho deve inicializar o firmware original e o display deve
   mostrar a inicialização normal do RP500; o USB deve enumerar como
   **`VID_1210 / PID_0016`** (DigiTech RP500).

---

## 5. Sobre o 1 MB superior

O updater do RP500 endereça apenas **16 x 64 KB = 1 MB**, então o firmware
fica na **primeira metade** do chip de 2 MB. O 1 MB superior está fora do
mapa do updater.

- Se o 1 MB superior original estiver **todo `0xFF`**, o arquivo preenchido
  está correto.
- Se o 1 MB superior original tiver dados, **não sobrescreva**: grave o 1 MB
  original na metade inferior e restaure a metade superior original (mescle
  `stock_1mb.bin` + `orig_2mb.bin[0x100000:0x200000]`).

---

## 6. Não faça

- **Não** use tensão de 5 V.
- **Não** mexa no **U19 (TAS1020B)** nem na pequena EEPROM I²C dele. É o
  controlador USB e não faz parte deste reparo.
- **Não** grave a imagem 2.2 S3b que falhou (`be9676…`).
- **Não** ligue o aparelho com o U26 removido.

---

## 7. Como saber que deu certo

- Display: inicialização normal do RP500, sem desligar em seguida.
- USB: `VID_1210 / PID_0016`.
- O aparelho aceita o firmware 2.0 original e funciona normalmente.

Se não inicializar, confira o pino 1, as soldas e o resultado da verificação
antes de mexer em qualquer outra coisa.

---

## 8. Custo realista

O único item especial é o **adaptador TSOP48 0,5 mm**. Qualquer oficina que
faz BIOS/EC/firmware embarcado já tem um T48 ou TL866 e o adaptador; o
serviço em si leva 15–30 minutos. Se não tiverem o adaptador, essa é a única
compra — e ainda é muito mais barato do que uma placa nova ou um chip
pré-gravado.
