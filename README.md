# Tugas Besar Kecerdasan Buatan — Tahap 4

## Deskripsi

Proyek ini merupakan pengembangan lanjutan dari **Tugas Besar Kecerdasan Buatan Tahap 3**. Tahap 4 menambahkan tiga kemampuan pada NPC: penalaran dengan **Knowledge Base First-Order Logic**, **Automated Planning**, dan pemilihan tim di bawah ketidakpastian (**Decisions Under Uncertainty**). Pertempuran _turn-based_ dengan _adversarial search_ (Minimax & Alpha-Beta Pruning) dari Tahap 2 tetap menjadi pengambil keputusan akhir.

Sistem terdiri atas tiga mode utama secara berurutan:

1. **Overworld** — Pemain dan NPC bergerak pada lingkungan grid. NPC menggunakan algoritma **A\*** untuk pathfinding menuju posisi pemain (tidak berubah dari tahap sebelumnya).

2. **Select (Pre-Battle Drafting)** — Setelah pemain memilih 3 Pokémon, sistem menyusun 3 Pokémon untuk NPC B dari 10 pilihan yang tersedia. Satu kali tekan `SPACE` menjalankan dua tahap berurutan:
   - **Constraint Satisfaction Problem (CSP)** dengan Backtracking, Heuristik (MRV, Degree, LCV), Inferensi AC-3, dan Branch-and-Bound Pruning, yang menghasilkan tim awal (_seed_).
   - **Local Search (Steepest Ascent Hill Climbing)** dengan **expected utility (EU)** sebagai fungsi objektif, dimulai dari tim hasil CSP. Hasilnya menjadi roster akhir NPC B.

3. **Battle** — Simulasi turn-based antara tepat dua NPC. NPC A memakai tim pemain dan NPC B memakai roster hasil Select. Pada setiap giliran, satu NPC menjalankan enam tahap: observasi, inferensi KB, planning, adversarial search kedalaman 2, pemilihan aksi, dan eksekusi. Pemain hanya memajukan simulasi.

## Fitur Utama Tahap 4

- **Logic & Representasi Pengetahuan:** Fakta dan **19 aturan** (R1–R10, P1–P5, G1–G4) disimpan pada berkas JSON terpisah dari kode. _Inference engine_ memakai **forward chaining** (generalized modus ponens dengan unifikasi) sampai titik tetap. Operasi KB: `tell`, `update_observations`, `infer`, dan `ask` (_entailed_ / _contradicted_ / _unknown_).
- **Automated Planning:** Tujuan (`recover`, `finish`, `win`) diturunkan oleh aturan KB (`PlanGoal`). Planner mencari rencana dengan **A\* berbasis simulator pertempuran** (`simulate_move()`), dengan _state_ berupa HP, defense, dan PP setiap Pokémon. Batas pencarian: 2500 ekspansi dan 80 ms. Langkah pertama rencana divalidasi dengan _dry run_ lalu dipakai sebagai _plan hint_.
- **Decisions Under Uncertainty:** Pemilihan tim NPC B dirumuskan sebagai keputusan dengan aturan _maximum expected utility_. Skenarionya adalah Pokémon pemain yang menjadi lawan, dengan probabilitas seragam 1/|P| (asumsi pemodelan, bukan data pemakaian). Utility skenario adalah −|margin keunggulan elemen|, sehingga tim yang seimbang bernilai paling tinggi.
- **Integrasi dengan Adversarial Search:** Hint dari KB dan planner hanya mengubah urutan evaluasi aksi. Aksi rencana dipilih bila nilainya berada dalam `plan_tolerance` (50) dari nilai terbaik; selain itu, aksi terbaik menurut Minimax / Alpha-Beta tetap dipakai.
- **Pengali Keunggulan Elemen:** Membaca relasi dari `weaknesses.txt` (56 pasangan keunggulan) yang diterapkan pada transisi _battle_ (pengali damage 1.5x atau 1/1.5x).
- **Tiga Debug Overlay Baru:** Overlay Knowledge Base (`I`), Planning (`P`), dan Decisions Under Uncertainty (`F3`), selain overlay Local Search (`M`), CSP (`C`), dan Node Tree (`N`) dari tahap sebelumnya.

## Struktur Utama Program

```
tubes_pokemon/
├── README.md
└── src/
    ├── main.py
    ├── battle.py
    ├── selection.py
    ├── uncertainty.py
    ├── knowledge_base.py
    ├── inference_engine.py
    ├── battle_interaction.py
    ├── battle_planning.py
    ├── planning.py
    ├── maze.py
    ├── config.py
    ├── utils.py
    └── assets/
        ├── weaknesses.txt
        ├── knowledge_base/
        │   ├── battle_facts.json
        │   └── battle_rules.json
        └── planning/
            └── battle_domain.json
```

### Fungsi Utama Berkas

| Berkas                  | Status | Fungsi                                                                                                                                                                                                             |
| ----------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `main.py`               | Diubah | Menjalankan _game loop_, navigasi overworld, transisi fase select dan battle, kemajuan giliran dua NPC, serta manajemen _debug overlay_ (M, C, F3, I, P, N).                                                       |
| `battle.py`             | Diubah | Mengatur state battle dua NPC, pembentukan fakta observasi (`_observed_facts()`), pemanggilan inferensi dan planner, `choose_action()` dengan hint, Minimax/Alpha-Beta kedalaman 2, serta overlay KB dan planning. |
| `selection.py`          | Diubah | Agen penyusun tim NPC: **CSP** (`choose_rival_team()`) dan **Local Search dengan EU** (`choose_rival_team_old()`), serta overlay Local Search, CSP, dan Decisions Under Uncertainty.                               |
| `uncertainty.py`        | Baru   | Skenario, utility, _expected utility_, dan `evaluate_team()`; memvalidasi bahwa probabilitas berada pada [0, 1] dan berjumlah 1.                                                                                   |
| `knowledge_base.py`     | Baru   | Kelas `Atom`, `Rule`, dan `KnowledgeBase`; memuat fakta dan aturan dari JSON.                                                                                                                                      |
| `inference_engine.py`   | Baru   | `InferenceEngine.infer()`: forward chaining sampai titik tetap, beserta rekaman evaluasi aturan dan derivasi untuk overlay.                                                                                        |
| `battle_interaction.py` | Baru   | `ActionHint` dan `PlanHint`; memetakan dan memvalidasi konklusi KB menjadi aksi battle.                                                                                                                            |
| `battle_planning.py`    | Baru   | Planner pertempuran: observasi state, kandidat tujuan dari KB, A\* dengan simulator, dan validasi langkah pertama.                                                                                                 |
| `planning.py`           | Baru   | Struktur data planning (`Action`, `PlanStep`, `PlanResult`, `PlanningDomain`) dan rutinitas planning umum. Rutinitas pencarian umumnya belum dipanggil oleh planner pertempuran (lihat Keterbatasan).              |
| `maze.py`               | Tetap  | Membentuk representasi grid/graf dari peta dan hubungan antar-_node_.                                                                                                                                              |
| `config.py`             | Diubah | Konfigurasi sistem: `ai_type`, `use_planning`, `planner_method`, `plan_tolerance`, `planner_max_expansions`.                                                                                                       |
| `utils.py`              | Tetap  | Fungsi untuk mengubah skala, rotasi, dan membalik sprite.                                                                                                                                                          |
| `assets/`               | Diubah | Aset visual, `weaknesses.txt`, fakta dan aturan KB (JSON), serta `battle_domain.json` (`goal_priority` dan `hp_bands`).                                                                                            |

## Persyaratan & Instalasi

- **Python 3**
- **Pygame-ce** (diuji pada pygame-ce 2.5.8, Python 3.12).

Instalasi dependensi:

```bash
python -m pip install pygame-ce
```

Jalankan program dari folder `src` agar aset relatif seperti gambar dan font dapat ditemukan:

```bash
cd src
python main.py
```

## Konfigurasi (`config.py`)

| Parameter                | Nilai bawaan   | Keterangan                                                                                                                |
| ------------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `ai_type`                | `"alpha-beta"` | Jenis adversarial search: `"minimax"` atau `"alpha-beta"`.                                                                |
| `use_planning`           | `True`         | Mengaktifkan lapisan planning (hint tingkat trainer hanya dipakai bila `True`).                                           |
| `planner_method`         | `"forward"`    | Nilai `"backward"` diterima tetapi pencarian tetap forward A\* simulasi.                                                  |
| `plan_tolerance`         | `50`           | Selisih nilai terbesar dari aksi terbaik agar langkah pertama rencana tetap diikuti (bobot HP 10, jadi setara 5 poin HP). |
| `planner_max_expansions` | `2500`         | Batas ekspansi simpul planner (batas waktu 80 ms ada pada `plan_battle_turn`).                                            |

## Kontrol Permainan

| Mode      | Tombol    | Fungsi                                                                                    |
| --------- | --------- | ----------------------------------------------------------------------------------------- |
| Overworld | `↑ ↓ ← →` | Menggerakkan pemain.                                                                      |
| Select    | `SPACE`   | Pertama: menjalankan CSP lalu Local Search EU. Kedua: memulai battle.                     |
| Select    | `↑ ↓`     | Tanpa overlay: memilih slot pemain. Dengan overlay terbuka: mundur/maju satu entri jejak. |
| Select    | `← →`     | Mengganti Pokémon pada slot pemain yang terpilih.                                         |
| Select    | `M`       | Membuka/menutup **Local Search Overlay**.                                                 |
| Select    | `C`       | Membuka/menutup **CSP Backtracking Overlay**.                                             |
| Select    | `F3`      | Membuka/menutup **Decisions Under Uncertainty Overlay**.                                  |
| Battle    | `SPACE`   | Memajukan tepat satu giliran seorang NPC.                                                 |
| Battle    | `I`       | Membuka/menutup **KB Overlay** (jejak evaluasi aturan).                                   |
| Battle    | `P`       | Membuka/menutup **Planning Overlay**.                                                     |
| Battle    | `N`       | Menampilkan/menyembunyikan **Node Tree** pencarian alpha-beta.                            |
| Battle    | `↑ ↓`     | Saat overlay I atau P terbuka: menelusuri evaluasi aturan atau langkah rencana.           |
| Battle    | `Q / W`   | Menggulir riwayat log _battle_.                                                           |
| Semua     | `ESC`     | Keluar dari program.                                                                      |

Pada mode Select, overlay M, C, dan F3 saling meniadakan; pada mode Battle, overlay I, P, dan N saling meniadakan.

## Pemodelan Masalah AI (Tahap 4)

### 1. Knowledge Base dan Forward Chaining

- **Representasi:** Atom FOL `Atom(predicate, arguments, negated)` dengan identitas `NPC_A` dan `NPC_B`, kepemilikan Pokémon, kondisi hidup/HP/move, serta keunggulan tipe. Argumen berawalan `?` adalah variabel. Seluruh aturan berbentuk klausa definit (Horn): konjungsi literal positif mengimplikasikan satu literal.
- **Fakta:** Fakta dasar dimuat dari `battle_facts.json`; fakta observasi dibentuk ulang pada setiap giliran oleh `_observed_facts()`.
- **Aturan:** R1–R10 (maksud aksi tingkat trainer), P1–P5 (maksud aksi tingkat Pokémon), dan G1–G4 (tujuan planning).
- **Inferensi:** Setiap aturan dievaluasi berurutan, kondisi dicocokkan dengan `_unify()`, dan konklusi langsung ditambahkan ke himpunan fakta sampai satu iterasi penuh tidak menurunkan fakta baru.
- **Pemakaian:** Konklusi `ActionIntent` dan `PokemonActionIntent` menjadi hint yang hanya memengaruhi urutan evaluasi aksi.
- **Keterbatasan:** `UnderStatusEffect` tidak pernah dibentuk karena game belum memiliki status effect, sehingga aturan R4, R9, dan P4 tidak pernah menurunkan konklusi.

### 2. Automated Planning

- **State:** Tuple per Pokémon (HP, defense, PP setiap aksi) untuk kedua sisi.
- **Aksi:** `attack`, `heal`, dan `rest` (aksi `defend` tidak direncanakan). Setiap aksi berbiaya 1.
- **Transisi:** Hasil aksi dihitung oleh `simulate_move()` pada salinan Pokémon.
- **Tujuan:** `recover`, `finish`, atau `win`, berasal dari `PlanGoal` hasil inferensi KB dan diurutkan oleh `goal_priority`.
- **Pencarian:** A\* maju dengan prioritas f = g + 2h, h berupa batas bawah jumlah aksi, serta batas 2500 ekspansi dan 80 ms. Status hasil: `plan`, `no-plan`, atau `limit`.
- **Validasi:** Langkah pertama diuji dengan _dry run_ sebelum menjadi plan hint.

### 3. Adversarial Search

- **Algoritma:** Minimax / Alpha-Beta Pruning, kedalaman 2.
- **Evaluasi:** E(S) = Σ u(p) tim sendiri − Σ u(p) tim lawan, dengan u = 10·HP + 2·DEF. Nilai terminal ±100000.
- **Urutan evaluasi:** Aksi plan hint, lalu aksi yang didukung KB, lalu indeks pelaku, sasaran, dan aksi. Aksi rencana dipilih bila nilainya berada dalam `plan_tolerance` dari nilai terbaik.

### 4. Decisions Under Uncertainty (Pemilihan Tim NPC B)

- **Skenario:** Setiap Pokémon pemain, dengan probabilitas seragam 1/|P|.
- **Margin:** m(T, p) = jumlah (keunggulan r atas p − keunggulan p atas r) untuk setiap r pada tim T.
- **Utility:** U = −|m|, sehingga nol berarti seimbang.
- **Expected utility:** EU(T) = Σ P(skenario) · U(skenario).
- **Pencarian:** _Steepest ascent hill climbing_ dari tim CSP; _neighbour_ dibentuk dengan mengganti satu slot dengan satu kandidat di luar tim, dan perpindahan diterima hanya bila EU lebih besar. Karena EU tidak aditif terhadap anggota tim, optimum global tidak dijamin.

### 5. Constraint Satisfaction Problem (dari Tahap 3)

- **Variabel (X):** X = {X1, X2, X3} (tiga slot tim NPC).
- **Domain (D):** Daftar Pokémon di luar tim pemain.
- **Constraint:** _All-different_ antar slot.
- **Optimasi & Pencarian:** Backtracking dengan MRV, Degree, LCV, **AC-3**, dan **Bound-Pruning** berdasarkan skor keunggulan aditif.

## Hasil Eksperimen Ringkas

Berdasarkan pengujian pada 120 kombinasi tim pemain (fungsi asli `choose_rival_team()` dan `choose_rival_team_old()`, tanpa membuka jendela):

- **Optimalitas EU:** CSP saja mencapai EU optimum pada **4 dari 120** kombinasi. CSP lalu Local Search EU mencapainya pada **111 dari 120** kombinasi (92,5%). Pada 9 kombinasi (termasuk tim pemain bawaan) Local Search berhenti di _local maximum_, sesuai dengan sifat EU yang tidak aditif.
- **Biaya Local Search dari tim CSP:** rata-rata 1,41 langkah (maksimum 3) dan 28,90 _neighbour_ dievaluasi (maksimum 48).
- **Derau float:** Perbandingan `>` tanpa toleransi dapat menerima penggantian yang hanya berbeda pada digit terakhir. Pada tim pemain bawaan, hal ini mengubah roster NPC B dari MEGUNIM, RAPIDASH, ONYX menjadi PIKACHU, RAPIDASH, ONYX.
- **Pertempuran tidak berakhir:** HEAL (+20 HP) dan REST (mengembalikan PP) tanpa batas giliran membuat pertempuran dapat berlanjut tanpa pemenang. Pada eksperimen laporan, 48 dari 48 pertempuran belum selesai setelah 80 giliran.

Rincian eksperimen E1–E6 (ukuran inferensi dan planning, perbandingan minimax vs alpha-beta, pengaruh `plan_tolerance`) terdapat pada Bab IV laporan. Waktu eksekusi bergantung pada mesin.

## Keterbatasan yang Diketahui

- Aturan R4, R9, dan P4 tidak pernah aktif karena game belum memiliki status effect.
- `planner_method = "backward"` tidak menjalankan pencarian mundur; `forward_search`, `regression_search`, dan `planning_graph` pada `planning.py` belum dipakai oleh planner pertempuran.
- Planner bersifat single-agent dan hanya langkah pertama rencana yang dipertimbangkan; rencana disusun ulang pada setiap giliran.
- Perbandingan EU memakai `>` tanpa toleransi float, dan Local Search tidak dijamin mencapai optimum global.
- `next_pokemon()` dan `prev_pokemon()` dari Tahap 3 belum diperbaiki: salinan Pokémon pengganti tidak dikenali sebagai anggota tim pemain sehingga kandidat dapat berjumlah lebih dari tujuh dan rival dapat memilih Pokémon yang sama dengan pemain.
- Probabilitas skenario seragam merupakan asumsi pemodelan, bukan hasil pengamatan.

## Demo dan Repositori

- **Demo Web (GitHub Pages):** `[isi tautan Tahap 4]`
- **Repositori Git:** `[isi tautan branch Tahap 4; jangan memakai branch main]`
- **Video Demo YouTube:** `[isi tautan]`

## Tim Penyusun

- **Ariq Ahmad Fathir** — 2506752
- **Fakhri Fauzan** — 2501536
- **Osman Mammedov** — 2522057

**Program Studi Ilmu Komputer**  
**Fakultas Pendidikan Matematika dan Ilmu Pengetahuan Alam**  
**Universitas Pendidikan Indonesia**  
**2026**
