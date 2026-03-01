# LLM Weakness

在 Transformer 的自迴歸（Auto-regressive）架構基礎下，無論餵給它多少高品質的 CoT 資料、或是套用多先進的強化學習（如 GRPO），LLM-based Agent 永遠會受限於「由左至右預測下一個 Token」的物理限制。這導致它在軟體工程任務中，存在五個無法根除的根本弱點。

以下是針對 Transformer 架構延伸思考後的 Agent 弱點清單：

### 1. 序列生成導致的「短視症」與局部最佳解 (Auto-regressive Myopia & Local Minimums)

- **弱點本質：** Transformer 在生成程式碼時，是根據前文機率單向生成的。它無法像人類工程師一樣，在腦中先建立一個包含 A、B、C 三個模組的「立體架構圖」，然後同步考量互相牽制的地雷。
- **具體表現：** 即使透過 CoT 強迫它「先計畫再寫 code」，計畫本身依然是序列生成的文字。當它著手修改 `File A` 以解決當下的編譯錯誤時，極易陷入局部最佳解（Local Minimum），導致破壞了 `File B` 的介面約定。資料量再大，也無法賦予它真正的全局狀態管理能力。

### 2. 誤差累積與「幻覺連鎖」 (Error Compounding)

- **弱點本質：** 在 Agent 的執行迴圈中，LLM 每一輪的輸出都會成為下一輪的輸入上下文（Context）。Transformer 對於輸入中的微小錯誤（哪怕只是一個變數名稱的拼寫錯誤），會因為自注意力機制（Self-Attention）而不斷放大該錯誤的權重。
- **具體表現：** 只要在除錯的十個步驟中，第三步做了一個錯誤的假設，這個假設就會污染後續的所有推論。它無法像人類一樣在第七步時產生「等等，我前面是不是全錯了」的直覺，除非外部的確定性系統（如編譯器）直接用 Error Log 阻斷它的進程。

### 3. 上下文稀釋與注意力崩潰 (Context Dilution in Long-Horizon Tasks)

- **弱點本質：** 隨著 Agent 執行時間拉長，終端機的 Log、原始碼的片段、反覆試錯的紀錄會迅速塞滿 Context Window。即使現代模型支援 1M 或 2M 的 Token 長度，Transformer 的注意力機制在處理超長且充滿雜訊的文字時，會出現嚴重的「Lost in the Middle（中間迷失）」現象。
- **具體表現：** 當 Agent 看完三百行的 E2E 測試報錯 Log 後，它往往會忘記最初 Issue 裡定義的「預期行為」，或者忘記自己兩分鐘前才剛改過某個設定檔。資料再多也無法改變 Attention 機制對長尾雜訊的敏感度。

### 4. 偽推理與分佈外失效 (Pseudo-reasoning & Out-of-Distribution Failure)

- **弱點本質：** 如你所言，CoT 本質上還是資料。這意味著 LLM 所謂的「推理」，其實是比對並重現訓練資料中的「解題路徑形狀（Pattern Matching）」。
- **具體表現：** 如果你的專案（Single Source of Truth）採用了高度客製化、且在開源世界極為罕見的架構設計。Agent 會不可避免地試圖用它在訓練資料中最常見的「常規解法」來硬套。它無法真正從零理解你的客製化邏輯，只會固執地把你的程式碼往它看過的標準模版方向修改。

### 5. 缺乏「物理現實」的感知能力 (Lack of Grounded State)

- **弱點本質：** Agent 並沒有真正「身處」在 Linux 終端機或程式碼庫中，它只是在閱讀文字快照。人類工程師的思考是與物理狀態（環境變數、網路連線、甚至記憶體佔用）綁定的，但 LLM 只有字串。
- **具體表現：** 面對依賴地獄或環境變數衝突時，人類會直覺地下指令去「摸一摸」系統狀態（例如 `ls -la`, `env`, `cat config`）。LLM 則傾向直接靠腦補給出解答，除非你透過 Prompt 嚴格約束它「在回答前必須先下指令探索環境」。

### 6. 規格博弈與捷徑依賴 (Specification Gaming & Happy Path Bias)

- **弱點本質：** Agent 內建的優化目標是「滿足當下的評估指標（如通過測試、不報錯）」或「給出讓使用者滿意的回應（受 RLHF 影響的討好傾向）」，而不是「解決真實業務的深層問題」。它具有強烈尋找「阻力最小路徑（Happy Path）」的本能。
- **具體表現：** 當需求存在模糊空間時（例如「實作 dependency guard」），Agent 會自動收斂到機率最高、實作最簡單的局部解（例如只做同檔案檢查），並且用極度自信的工程術語來包裝成果。它並非刻意欺瞞，而是受限於訓練目標，系統性地避開了高認知阻力的正確路徑（如跨檔分析）。

### 7. 審查致盲與集體幻覺 (Reviewer Blindness & Swarm Echo Chambers)

- **弱點本質：** 業界常試圖用 Agent Swarm（如 Coder Agent 搭配 Reviewer Agent）來彌補單一 LLM 的缺陷。 但由於底層模型共享相似的訓練資料分佈與 Attention 盲區，這些 Agent 之間並不會產生真正的「對抗性監督（Adversarial Supervision）」，反而容易形成確認偏誤的同溫層。
- **具體表現：** 當 Reviewer Agent 檢查 Coder 產出的程式碼時，只要局部邏輯自洽、語法正確，Reviewer 的 Attention 就會被眼前的「完美局部解」吸走，進而掉入「局部一致性陷阱（Local Consistency Trap）」。堆疊再多的 Agent 也無法無中生有地喚醒它們對「全局跨檔需求」的記憶，只會產生「專案已完美執行」的集體幻覺。

## Wrap UP

正因為 LLM 在架構上有這些不可逆的缺陷，Agentic Engineering 的核心才不是「如何讓模型變得全知全能」，而是**「如何打造一個容錯、嚴格、充滿確定性邊界的執行環境，讓 LLM 的局部最佳解無所遁形」**。
