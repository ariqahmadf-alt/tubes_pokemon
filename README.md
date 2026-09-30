# Tugas Besar Kecerdasan Buatan — Tahap 2

## Deskripsi

Proyek ini merupakan pengembangan dari Tugas Besar Kecerdasan Buatan Tahap 1 berupa simulasi lingkungan **open field berbasis grid** dengan tambahan **pertempuran turn-based**.

Sistem terdiri atas dua mode utama:

1. **Overworld** — pemain dan NPC bergerak pada lingkungan berbasis grid. NPC menggunakan algoritma **A\*** untuk mencari jalur menuju posisi pemain setelah pemain terdeteksi.
2. **Battle** — setelah kondisi pertemuan terpenuhi, sistem berpindah ke lingkungan pertempuran terpisah. NPC menentukan aksi menggunakan **Minimax** atau **Alpha-Beta Pruning**.

Fokus kecerdasan buatan pada Tahap 2 adalah pengambilan keputusan agen NPC dalam lingkungan pertempuran melalui **adversarial search**.

## Fitur

- Pergerakan karakter pada lingkungan grid.
- Pathfinding NPC pada overworld menggunakan **A\*** dengan heuristik Manhattan.
- Transisi dari overworld ke mode battle setelah NPC mendeteksi pemain.
- Pertempuran turn-based.
- Empat aksi battle:
  - `ATTACK`
  - `DEFEND`
  - `HEAL`
  - `REST`
- Pengambilan keputusan NPC menggunakan:
  - Minimax
  - Alpha-Beta Pruning
- Variasi kedalaman pencarian.
- Variasi bobot fungsi evaluasi.
- Eksperimen pengaruh urutan aksi terhadap Alpha-Beta Pruning.
- **AI Brain** untuk menampilkan proses pengambilan keputusan NPC.
- **Node Tree** untuk melihat struktur pencarian.
- **Battle Log** untuk melihat riwayat aksi.

## Struktur Program

```text
tubes_pacman/
├── main.py
├── battle.py
├── maze.py
├── config.py
├── assets/
└── README.md
```

### Fungsi utama berkas

| Berkas | Fungsi |
|---|---|
| `main.py` | Menjalankan game loop, pergerakan overworld, transisi battle, dan alur giliran. |
| `battle.py` | Menangani state battle, aksi, simulasi state, fungsi evaluasi, Minimax, Alpha-Beta, serta debug overlay. |
| `maze.py` | Membentuk representasi grid/graf dari peta dan hubungan antar-node. |
| `config.py` | Menyimpan konfigurasi sistem, termasuk mode AI battle dan parameter overworld. |
| `assets/` | Menyimpan aset visual yang digunakan oleh sistem. |

## Persyaratan

- Python 3
- Pygame

Instalasi dependensi:

```bash
pip install pygame
```

Menjalankan program:

```bash
python main.py
```

## Kontrol

| Tombol | Fungsi |
|---|---|
| `↑ ↓ ← →` | Menggerakkan pemain / memilih aksi sesuai mode |
| `SPACE` | Melanjutkan proses atau giliran |
| `K` | Menampilkan informasi AI |
| `N` | Menampilkan Node Tree |
| `M` | Menampilkan Move Log / AI Brain |
| `S` | Menggunakan konfigurasi fungsi evaluasi A |
| `A` | Menggunakan konfigurasi fungsi evaluasi B |
| `D` | Menggunakan konfigurasi fungsi evaluasi C |
| `Q / W` | Menggulir informasi log |
| `ESC` | Keluar dari tampilan / program |

## Model Battle

State battle merepresentasikan kondisi kedua agen menggunakan beberapa atribut utama:

- HP pemain dan NPC
- Defense pemain dan NPC
- PP/action availability pemain dan NPC

Aksi yang tersedia adalah:

| Aksi | Fungsi |
|---|---|
| `ATTACK` | Memberikan damage kepada lawan berdasarkan nilai serangan dan Defense target. |
| `DEFEND` | Meningkatkan Defense sehingga damage yang diterima dapat berkurang. |
| `HEAL` | Memulihkan HP. Dalam spesifikasi tugas, aksi ini merupakan padanan dari aksi potion. |
| `REST` | Memulihkan Power Points (PP). |

NPC merupakan agen **MAX**, sedangkan pemain diperlakukan sebagai agen **MIN** dalam pencarian adversarial.

## Minimax dan Alpha-Beta Pruning

Pada mode battle, NPC mengevaluasi kemungkinan aksi melalui game tree hingga kedalaman pencarian tertentu.

Fungsi evaluasi utama menggunakan bobot HP dan Defense:

```text
E(S) = 10(HP_NPC - HP_Player)
     + 2(Defense_NPC - Defense_Player)
```

Kondisi terminal diberi nilai utilitas yang besar untuk membedakan kondisi menang dan kalah.

Konfigurasi AI battle pada program menggunakan **Alpha-Beta Pruning**, sedangkan implementasi Minimax juga tersedia untuk perbandingan eksperimen.

## Eksperimen Utama

Eksperimen dalam laporan membandingkan Minimax dan Alpha-Beta pada beberapa kedalaman pencarian serta variasi fungsi evaluasi dan urutan aksi.

Contoh hasil pada depth 2:

| Metode | Nodes | Leaves | Pruned | Aksi | Skor |
|---|---:|---:|---:|---|---:|
| Minimax | 21 | 16 | 0 | ATTACK | -50 |
| Alpha-Beta | 12 | 7 | 9 | ATTACK | -50 |

Hasil eksperimen menunjukkan bahwa pada state uji yang digunakan, Minimax dan Alpha-Beta menghasilkan aksi dan skor akar yang sama, sedangkan Alpha-Beta mengevaluasi lebih sedikit node.

**Catatan:** waktu eksekusi tidak diukur dalam eksperimen yang dilaporkan.

## Debug dan Visualisasi

Sistem menyediakan beberapa tampilan untuk membantu pemeriksaan proses AI:

- **AI Brain** — menampilkan aksi yang dipertimbangkan, skor, depth, dan informasi pencarian.
- **Node Tree** — menampilkan struktur game tree.
- **Battle Log** — menampilkan urutan aksi selama pertempuran.

## Demo dan Repositori

- Demo Web (GitHub Pages): https://ariqahmadf-alt.github.io/tubes_pokemon/
- Repositori Git: https://github.com/ariqahmadf-alt/tubes_pokemon/tree/node-overlay
- Video Demo: https://youtu.be/i6IImxUEIKA

## Tim

- Ariq Ahmad Fathir — 2506752
- Fakhri Fauzan — 2501536
- Osman Mammedov — 2522057

**Program Studi Ilmu Komputer**  
**Universitas Pendidikan Indonesia**  
**2026**
