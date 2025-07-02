# SHFQC 圖形化控制程式

本專案提供一套以 **Python** 編寫的圖形化介面，用於控制 Zurich Instruments 的 **SHFQC** 量測設備。程式主體位於 `SHFQC UI/SHFQC 穩定版本.py`，結合了多個輔助模組，可進行波形產生、儀器控制、量測流程管理以及量測數據存取與繪圖等功能。

## 專案結構

- `SHFQC UI/SHFQC 穩定版本.py`：主程式入口，建立並啟動圖形化介面。
- `SHFQC UI/library/`
  - `device_control.py`：與 SHFQC 及 YOKOGAWA 等儀器的通訊接口。
  - `waveform_generation.py`：依照參數或自定義公式產生波形。
  - `measurement_controller.py`：負責量測流程控制及即時監看。
  - `File_Storage.py`：量測資料儲存與讀取工具。
  - `Formula_Parser.py`：解析自訂公式並評估結果。
  - `gui_components.py`、`MainUI_builder.py`：介面元件與主畫面佈局。
  - `plot_manager.py`：將量測結果繪製於介面上。
  - `config_handler.py`：載入與儲存 `shfqc_config.ini` 設定檔。
- `SHFQC UI/shfqc_config.ini`：預設設定檔，儲存各項參數與 UI 狀態。

## 安裝與執行

1. **環境需求**
   - Python 3.8 以上版本。
   - 建議安裝下列套件：
     - `PyQt6`
     - `numpy`
     - `scipy`
     - `matplotlib`
     - `zhinst-toolkit`
     - `pyvisa`

   可使用 `pip` 依序安裝，例如：
   ```bash
   pip install PyQt6 numpy scipy matplotlib zhinst-toolkit pyvisa
   ```

2. **啟動程式**
   進入 `SHFQC UI` 目錄後執行：
   ```bash
   python "SHFQC 穩定版本.py"
   ```
   即可開啟圖形化介面。

## 設定檔說明

`shfqc_config.ini` 內存放程式啟動時載入的各項參數，關閉程式時也會將最新設定寫入其中。若需修改預設值，可直接編輯此檔案，但請避免更改其格式。

## 功能摘要

- 以 GUI 操作 SHFQC 進行時域或頻域量測，支援振幅掃描、頻率掃描與電流-頻率掃描等模式。
- 提供多種波形產生方式（高斯、方波、指數、自定義公式），並可將波形載入至儀器。
- 量測數據可即時繪製並儲存為 CSV 與圖片，便於後續分析。
- 可連接並控制 YOKOGAWA 電流源，配合量測自動掃描電流值。

## 其他注意事項

- 若遇到程式無法讀取 `shfqc_config.ini`，請確認檔案開頭是否含有 BOM，必要時以純文字編輯器重新儲存為 UTF-8 編碼。
- 本專案暫未提供自動化測試與完整的依賴版本要求，建議在虛擬環境中安裝套件以避免衝突。

歡迎後續維護者依需求擴充功能或補充文件，以利長期使用。

