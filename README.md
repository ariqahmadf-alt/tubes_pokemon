# Tugas Besar Kecerdasan Buatan — Tahap 3

## Deskripsi

Proyek ini merupakan pengembangan lanjutan dari **Tugas Besar Kecerdasan Buatan Tahap 2**, yang mengintegrasikan simulasi lingkungan **open field berbasis grid**, pertempuran **turn-based** menggunakan _adversarial search_ (Minimax & Alpha-Beta Pruning), serta penambahan sistem **Pre-Battle Drafting** otomatis untuk konfigurasi tim NPC.

Sistem terdiri atas tiga mode utama secara berurutan:

1. **Overworld** — Pemain dan NPC bergerak pada lingkungan grid. NPC menggunakan algoritma **A\*** untuk pathfinding menuju posisi pemain.

2. **Select (Pre-Battle Drafting)** — Setelah pemain memilih 3 Pokémon, sistem secara otomatis menyusun 3 Pokémon untuk NPC dari 10 pilihan yang tersedia menggunakan dua pendekatan AI:
   - **Local Search (Hill Climbing)**

   - **Constraint Satisfaction Problem (CSP)** dengan Backtracking, Heuristik (MRV, Degree, LCV), Inferensi AC-3, dan Branch-and-Bound Pruning.

3. **Battle** — Simulasi turn-based antara tepat dua NPC. Roster yang disiapkan pada Select disalin menjadi data NPC A (bukan Pokémon pemain dalam battle); NPC A dan NPC B menentukan aksi sendiri menggunakan Minimax atau Alpha-Beta Pruning. Pemain hanya memajukan simulasi. Knowledge Base FOL terpisah menurunkan interaksi NPC dan menampilkan jejak inferensinya.

## Fitur Utama Tahap 3

- **Formulasi Local Search (Hill Climbing):** Mengoptimalkan komposisi tim NPC secara iteratif berdasarkan skor keunggulan elemen V(T).

- **Formulasi CSP & Backtracking:** Menelusuri ruang penugasan secara sistematis, lengkap dengan:
  - Variabel, Domain, dan Constraint All-Different.

  - Inferensi arc-consistency (**AC-3**).

  - Heuristik pemilihan variabel (**MRV**, **Degree**) dan nilai (**LCV**).

  - **Bound-Pruning** berdasarkan batas atas skor aditif.

- **Pengali Keunggulan Elemen:** Membaca relasi dari `weaknesses.txt` (56 pasangan antarelemen dari 17 elemen) yang diterapkan pada transisi _battle_ (pengali damage 1.5x atau 1/1.5x).
- **Knowledge-Based Battle Agent:** Fakta dan aturan FOL deklaratif diproses dengan forward chaining, termasuk pilihan Pokémon pelaku dan target.
- **Dua NPC Berlawanan:** NPC A dan NPC B bergantian menentukan Pokémon hidup yang digunakan, target Pokémon lawan untuk serangan, dan move; SPACE hanya memajukan satu aksi NPC.
- **Perencanaan Battle:** Planner STRIPS menerjemahkan tujuan hasil inferensi menjadi urutan aksi abstrak, lalu pencarian adversarial memeriksa keamanan langkah pertama.

- **Debug Overlay:** Antarmuka untuk meninjau pencarian adversarial, inferensi, dan langkah-langkah perencanaan.

## Struktur Program

```
tubes_pokemon/
├── README.md
└── src/
    ├── main.py
    ├── battle.py
    ├── battle_planning.py
    ├── planning.py
    ├── selection.py
    ├── knowledge_base.py
    ├── inference_engine.py
    ├── battle_interaction.py
    ├── maze.py
    ├── config.py
    ├── utils.py
    └── assets/
        ├── weaknesses.txt
        ├── planning/
        │   └── battle_domain.json
        └── knowledge_base/
            ├── battle_facts.json
            └── battle_rules.json
```

### Fungsi Utama Berkas

| Berkas         | Fungsi                                                                                                                                                                |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py`      | Menjalankan _game loop_, navigasi overworld, transisi fase select, kemajuan giliran dua NPC, serta manajemen _debug overlay_. |
| `battle.py`    | Mengatur state battle dua NPC, aksi Pokémon, Minimax/Alpha-Beta, evaluasi, dan overlay battle. |
| `battle_planning.py` | Mengubah observasi battle dan tujuan KB menjadi problem perencanaan, lalu memvalidasi langkah pertama terhadap simulasi move. |
| `planning.py` | Menyediakan representasi STRIPS, grounding, transisi state, forward search, regression, heuristik h-max, dan planning graph. |
| `knowledge_base.py` | Memuat dan mengelola fakta serta aturan battle secara deklaratif. |
| `inference_engine.py` | Menjalankan forward chaining FOL dan merekam jejak inferensi aktual. |
| `battle_interaction.py` | Memvalidasi dan memetakan intent KB ke aksi battle yang tersedia. |
| `selection.py` | Mengimplementasikan agen penyusun tim NPC (**Hill Climbing** dan **CSP** lengkap dengan AC-3, LCV, MRV, Branch-and-Bound) serta overlay visualnya.                    |
| `maze.py`      | Membentuk representasi grid/graf dari peta dan hubungan antar-_node_.                                                                                                 |
| `config.py`    | Menyimpan konfigurasi sistem, parameter overworld, dan jenis AI _battle_.                                                                                             |
| `utils.py`     | Menyediakan fungsi untuk mengubah skala, rotasi, dan membalik sprite.                                                                                                  |
| `assets/`      | Menyimpan aset visual serta berkas relasi keunggulan elemen (`weaknesses.txt`).                                                                                       |

## Persyaratan & Instalasi

- **Python 3**
- **Pygame**

Instalasi dependensi:

```bash
python -m pip install pygame
```

Jalankan program dari folder `src` agar aset relatif seperti gambar dan font dapat ditemukan:

```bash
cd src
python main.py
```

Jalankan pengujian battle/KB dari folder `src`:

```bash
python -m unittest discover -s tests
```

## Kontrol Permainan

| Tombol      | Fungsi                                                                                                   |
| ----------- | -------------------------------------------------------------------------------------------------------- |
| `↑ ↓ ← →`   | Menggerakkan pemain di overworld; navigasi menu/debug Select; UP/DOWN menelusuri evaluasi aturan pada overlay KB. |
| `SPACE`     | Di Select, menjalankan pemilihan roster NPC dan memulai battle; di battle, memajukan tepat satu aksi AI NPC. |
| `M`         | Di Select, membuka/menutup **Local Search Overlay**; di battle, mengganti log aksi dan ringkasan search; di overworld, mengganti tampilan peta. |
| `I`         | Membuka/menutup overlay fakta dan jejak inferensi Knowledge Base battle. |
| `C`         | Membuka/menutup **CSP Backtracking Overlay** di Select.                                                   |
| `N`         | Menampilkan/menyembunyikan struktur _Node Tree_ di _battle_.                                               |
| `P`         | Membuka/menutup overlay perencanaan battle; UP/DOWN memilih langkah untuk melihat precondition dan state hasil. Membuka overlay `P`, `I`, atau `N` menutup dua overlay lainnya. |
| `Q / W`     | Menggulir riwayat log _battle_.                                                                           |
| `ESC`       | Keluar dari program.                                                                                      |

Mode pencarian dan bobot evaluasi diatur pada kode/config; pemain tidak dapat mengubah strategi NPC selama battle.

## Pemodelan Masalah AI (Tahap 3)

### 1. Battle Knowledge Base

- **Representasi:** Predikat FOL menggunakan identitas `NPC_A` dan `NPC_B`, kepemilikan Pokémon, kondisi Pokémon hidup/HP/move, target, serta keunggulan tipe.
- **Inferensi:** Forward chaining dengan pencocokan variabel hingga tidak ada fakta baru.
- **Interaksi:** Pada setiap giliran, pencarian adversarial mengevaluasi Pokémon hidup mana yang bertindak, move yang dipakai, dan target Pokémon lawan untuk serangan. Intent FOL yang spesifik Pokémon memandu urutan pilihan dan hasil aktor/target/move ditampilkan pada battle, log, dan overlay. Tekan `I` untuk meninjau fakta, rule, substitusi, kesimpulan, serta hasil validasi aksi. Informasi yang tidak diketahui tidak dianggap otomatis salah.
- Sistem battle saat ini belum memiliki status effect atau item; rule status tetap dapat diuji dengan fakta status, tetapi game tidak membuat kondisi status/item fiktif.

### 2. Automated Planning

- **State:** Fakta boolean tertutup untuk kepemilikan Pokémon, relasi keunggulan tipe, kesiapan move, status pertahanan, dan HP dalam band `high`, `mid`, `low`, atau `gone`. Band `low` memakai ambang yang sama dengan KB, yaitu HP ≤ 30% maksimum.
- **Action schemas:** `attack-advantaged`, `attack-neutral`, `attack-resisted`, `break-shield`, `defend`, `heal`, dan `rest` dideklarasikan di `assets/planning/battle_domain.json`. Aksi serangan dan pemulihan menggunakan efek tambah/hapus STRIPS; biaya serangan berturut-turut membedakan keunggulan, netral, dan resistansi.
- **Goal:** Rule KB memilih `recover`, `finish`, atau `win`. Domain menetapkan prioritas `recover` > `finish` > `win`; recovery mengarahkan Pokémon lemah ke band HP tinggi, finish menargetkan satu Pokémon lawan, dan win menargetkan seluruh roster lawan.
- **Planner:** Forward mode menggunakan A* dengan heuristik h-add delete-relaxation untuk pencarian praktis; h-max yang admissible tersedia untuk pencarian optimal melalui `config.planner_heuristic = "h_max"`. Backward mode menggunakan regression STRIPS. Planning graph dengan no-op dan mutex memberi batas bawah serta mendeteksi goal yang tidak terjangkau. Pencarian dibatasi berdasarkan ekspansi dan waktu.
- **Integrasi battle:** Planner hanya memberi saran langkah pertama. Langkah tersebut diuji melalui simulasi move pada salinan state; langkah yang tidak cocok dengan hasil abstraksi tidak digunakan. Minimax/Alpha-Beta tetap menghitung nilai tanpa perubahan; saran rencana hanya mengurutkan aksi dan dapat dipilih jika berada dalam toleransi skor. State diamati ulang dan rencana dibuat ulang setiap giliran.
- **Debug:** Tekan `P` untuk melihat goal dan rule KB, urutan aksi, precondition, state setelah langkah, statistik, dan alasan saat rencana tidak tersedia. UP/DOWN menelusuri langkah rencana.

### 3. Local Search (Hill Climbing)

- **State:** Tim NPC berupa 3 Pokémon berbeda yang bukan anggota tim pemain.
- **Neighbour:** Mengganti satu slot Pokémon dengan satu kandidat di luar tim (3 x (m - 3) kombinasi).
- **Fungsi Objektif:** Memaksimalkan skor keunggulan elemen V(T), yaitu jumlah nilai m(r) untuk setiap Pokémon r dalam tim T. Nilai m(r) adalah selisih keunggulan terhadap seluruh tim pemain.
- **Aturan:** _Steepest Ascent_ tanpa _random restart_ (hanya menerima perbaikan dengan skor yang lebih tinggi).

### 4. Constraint Satisfaction Problem (CSP)

- **Variabel (X):** X = {X1, X2, X3} (tiga slot tim NPC).
- **Domain (D):** Daftar Pokémon di luar tim pemain.
- **Constraint:** _All-different_ antar slot (setiap Xi berbeda dari Xj).
- **Optimasi & Pencarian:** Backtracking dengan heuristik MRV, Degree, LCV, inferensi **AC-3**, serta **Bound-Pruning** (memangkas cabang jika batas atas skor tidak melebihi skor terbaik saat ini).

## Hasil Eksperimen Ringkas

Berdasarkan pengujian pada 120 kombinasi tim pemain:

- **Optimalitas:** Baik Hill Climbing maupun CSP berhasil mencapai skor optimum pada **120 dari 120 kombinasi** (karena fungsi skor bersifat aditif sehingga tidak memiliki _local maximum_ semu).
- **Efisiensi Biaya:**
  - Hill Climbing rata-rata memerlukan 1.34 langkah dan mengevaluasi 28.1 _neighbour_.
  - CSP secara konsisten mencoba hanya 18 penugasan dan mencatat 15 _bound-prunes_ (jauh lebih efisien dibandingkan enumerasi penuh sebanyak 210 kombinasi).

## Demo dan Repositori

- **Demo Web (GitHub Pages):** https://ariqahmadf-alt.github.io/tubes_pokemon/
- **Repositori Git:** https://github.com/ariqahmadf-alt/tubes_pokemon/tree/csp
- **Video Demo YouTube:** https://youtu.be/vEMODdwTfHw

## Tim Penyusun

- **Ariq Ahmad Fathir** — 2506752
- **Fakhri Fauzan** — 2501536
- **Osman Mammedov** — 2522057

**Program Studi Ilmu Komputer**  
**Fakultas Pendidikan Matematika dan Ilmu Pengetahuan Alam**  
**Universitas Pendidikan Indonesia**  
**2026**
