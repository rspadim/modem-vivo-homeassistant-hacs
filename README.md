# Modem Vivo Home Assistant HACS

Integração customizada para Home Assistant/HACS e cliente Python para coletar status de modem Vivo/GVT `RTF8225VW` via interface web autenticada.

O fluxo de configuração sugere apenas o endereço e usuário mais comuns:

- usuário: `admin`
- senha: informe localmente no Home Assistant; não há senha padrão publicada no repositório

Não versione sua senha. Para uso via CLI/serviço, mantenha credenciais apenas no `config.json` local ou em variáveis de ambiente.

## Instalação via HACS

Enquanto o repositório não estiver na lista padrão do HACS:

1. HACS → três pontos → Custom repositories
2. URL: `https://github.com/rspadim/modem-vivo-homeassistant-hacs`
3. Categoria: `Integration`
4. Instale `Modem Vivo`
5. Reinicie o Home Assistant
6. Configurações → Dispositivos e serviços → Adicionar integração → `Modem Vivo`

## Publicação/Validação HACS

Este repositório inclui:

- `hacs.json`
- `custom_components/modem_vivo/manifest.json`
- `.github/workflows/validate.yml` usando `hacs/action@main`

O GitHub Action valida o repositório em pushes, PRs, execução manual e diariamente.

## Entidades Home Assistant

A integração exporta sensores principais e mantém polling local:

- GPON/PPP/DHCP/UPnP como `binary_sensor`
- IP público IPv4
- status e serial GPON
- potência óptica TX/RX
- uptime PPP
- canais e potência Wi-Fi
- hosts ativos vistos pelo modem
- contadores RX/TX por Ethernet/Wi-Fi
- taxa RX/TX Mbps por Ethernet/Wi-Fi calculada por delta entre coletas

Campos adicionais não sensíveis também são coletados em `raw_public_vars` no cliente Python, para facilitar criar novas entidades depois.

## Configuração

Crie um `config.json` com:

```json
{
  "ip": "192.168.0.1",
  "usuario": "admin",
  "senha": "sua-senha"
}
```

Também é possível usar variáveis de ambiente:

- `VIVO_MODEM_IP`
- `VIVO_MODEM_USUARIO`
- `VIVO_MODEM_SENHA`

## Uso

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m modem_vivo.cli --config config.json
```

## Serviço HTTP Local

O serviço mantém polling contínuo e calcula uso de banda usando delta dos contadores da página `device-management-statistics.asp`.

```bash
python -m modem_vivo.service --config config.json --host 127.0.0.1 --port 8765 --interval 30
```

Consultar:

```bash
curl http://127.0.0.1:8765/status
```

Na primeira coleta, `rates.ready` fica `false`. A partir da segunda coleta, o JSON inclui:

- `rates.ethernet.eth1..eth4.rx_mbps` / `tx_mbps`
- `rates.wifi.wl0.rx_mbps` / `tx_mbps`
- `rates.wifi.wl1.rx_mbps` / `tx_mbps`
- `rates.totals.ethernet_rx_mbps` / `ethernet_tx_mbps`
- `rates.totals.wifi_rx_mbps` / `wifi_tx_mbps`

## Dados Coletados

- Modelo, versão de software/hardware, MAC WAN/LAN
- Estado GPON/PPP
- IP público IPv4/IPv6, gateway e DNS
- Potência óptica TX/RX
- Configuração LAN/DHCP/UPnP
- Hosts vistos pelo modem
- SSID/canal de Wi-Fi 2.4 GHz e 5 GHz

## Home Assistant

O caminho principal é a integração HACS em `custom_components/modem_vivo`.

Alternativa mais eficiente: rodar `modem_vivo.service` como serviço local e usar sensores REST do Home Assistant apontando para `http://127.0.0.1:8765/status`.

Este cliente é somente leitura, desde que usado apenas com a CLI atual.
