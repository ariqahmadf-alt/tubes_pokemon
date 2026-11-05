# Tugas Besar Kecerdasan Buatan — Tahap 3

## Deskripsi

Proyek ini merupakan pengembangan lanjutan dari **Tugas Besar Kecerdasan Buatan Tahap 2**, yang mengintegrasikan simulasi lingkungan **open field berbasis grid**, pertempuran **turn-based** menggunakan _adversarial search_ (Minimax & Alpha-Beta Pruning), serta penambahan sistem **Pre-Battle Drafting** otomatis untuk konfigurasi tim NPC.

Sistem terdiri atas tiga mode utama secara berurutan:

1. **Overworld** — Pemain dan NPC bergerak pada lingkungan grid. NPC menggunakan algoritma **A\*** untuk pathfinding menuju posisi pemain.

2. **Select (Pre-Battle Drafting)** — Setelah pemain memilih 3 Pokémon, sistem secara otomatis menyusun 3 Pokémon untuk NPC dari 10 pilihan yang tersedia menggunakan dua pendekatan AI:
   - **Local Search (Hill Climbing)**

   - **Constraint Satisfaction Problem (CSP)** dengan Backtracking, Heuristik (MRV, Degree, LCV), Inferensi AC-3, dan Branch-and-Bound Pruning.

3. **Battle** — Pertempuran turn-based di mana NPC menentukan aksi menggunakan Minimax atau Alpha-Beta Pruning, dengan tambahan modifikasi pengali keunggulan elemen (k) yang memengaruhi perhitungan _damage_.

## Fitur Utama Tahap 3

- **Formulasi Local Search (Hill Climbing):** Mengoptimalkan komposisi tim NPC secara iteratif berdasarkan skor keunggulan elemen V(T).

- **Formulasi CSP & Backtracking:** Menelusuri ruang penugasan secara sistematis, lengkap dengan:
  - Variabel, Domain, dan Constraint All-Different.

  - Inferensi arc-consistency (**AC-3**).

  - Heuristik pemilihan variabel (**MRV**, **Degree**) dan nilai (**LCV**).

  - **Bound-Pruning** berdasarkan batas atas skor aditif.

- **Pengali Keunggulan Elemen:** Membaca relasi dari `weaknesses.txt` (56 pasangan antarelemen dari 17 elemen) yang diterapkan pada transisi _battle_ (pengali damage 1.5x atau 1/1.5x).

- **Dual Debug Overlays:** Antarmuka visual mendalam untuk meninjau langkah-langkah pencarian secara interaktif untuk kedua metode AI.

## Struktur Program

```
tubes_pokemon/
├── README.md
└── src/
    ├── main.py
    ├── battle.py
    ├── selection.py
    ├── maze.py
    ├── config.py
    ├── utils.py
    └── assets/
        └── weaknesses.txt
```

### Fungsi Utama Berkas

| Berkas         | Fungsi                                                                                                                                                                |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `main.py`      | Menjalankan _game loop_, navigasi overworld, transisi fase select, perulangan giliran _battle_, serta manajemen _debug overlay_.                                      |
| `battle.py`    | Mengatur state _battle_, logika aksi (`ATTACK`, `DEFEND`, `HEAL`, `REST`), transisi _simulate_move_ dengan pengali elemen, Minimax, Alpha-Beta, serta evaluasi state. |
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

## Kontrol Permainan

| Tombol      | Fungsi                                                                                                   |
| ----------- | -------------------------------------------------------------------------------------------------------- |
| `↑ ↓ ← →`   | Menggerakkan pemain di overworld; memilih aksi/Pokémon di menu; menelusuri langkah _debug_ di Select.    |
| `1 / 2 / 3` | Memilih Pokémon untuk aksi atau target di _battle_.                                                       |
| `SPACE`     | Di Select, pertama kali menjalankan pemilihan tim rival dan berikutnya masuk ke _battle_; melanjutkan giliran _battle_. |
| `M`         | Di Select, membuka/menutup **Local Search Overlay**; di luar Select, menampilkan/menyembunyikan log _battle_ (dan mengganti tampilan peta asli di overworld). |
| `C`         | Membuka/menutup **CSP Backtracking Overlay** di Select.                                                   |
| `K`         | Mengganti AI _battle_ antara Minimax dan Alpha-Beta Pruning.                                              |
| `N`         | Menampilkan/menyembunyikan struktur _Node Tree_ di _battle_.                                               |
| `S / A / D` | Memilih bobot evaluasi _battle_: S (HP 10, DEF 2), A (HP 25, DEF 1), atau D (HP 2, DEF 15).                    |
| `Q / W`     | Menggulir riwayat log _battle_.                                                                           |
| `ESC`       | Keluar dari program.                                                                                      |

## Pemodelan Masalah AI (Tahap 3)

### 1. Local Search (Hill Climbing)

- **State:** Tim NPC berupa 3 Pokémon berbeda yang bukan anggota tim pemain.
- **Neighbour:** Mengganti satu slot Pokémon dengan satu kandidat di luar tim (3 x (m - 3) kombinasi).
- **Fungsi Objektif:** Memaksimalkan skor keunggulan elemen V(T), yaitu jumlah nilai m(r) untuk setiap Pokémon r dalam tim T. Nilai m(r) adalah selisih keunggulan terhadap seluruh tim pemain.
- **Aturan:** _Steepest Ascent_ tanpa _random restart_ (hanya menerima perbaikan dengan skor yang lebih tinggi).

### 2. Constraint Satisfaction Problem (CSP)

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
