# Bouncing Ball Catcher - Proyek ROS2 & OpenCV

Proyek game interaktif berbasis **ROS2 Jazzy** dan **OpenCV** di mana pemain mengendalikan objek berwarna di depan kamera untuk menangkap beberapa bola virtual yang memantul dan bertahan selama 2 detik berturut-turut guna mendapatkan skor.

---

## 1. Link Video Demo
Tonton video demo pengujian game, deteksi objek, dan fitur bonus di sini:
**(https://drive.google.com/file/d/1EsLOGvPVOS46cXSdeelBE55Uo0BXo1e0/view?usp=drive_link)**

---

## 2. Arsitektur Sistem & Topik
Sistem ini terdiri dari dua node utama yang berjalan di dalam package ROS2 `bouncing_ball_catcher`:

- **`camera_node`**: Membaca *frame* gambar dari webcam atau file video (mendukung *auto-loop* jika video habis) dan mempublikasikannya ke topik `/camera/image_raw` (`sensor_msgs/msg/Image`).

- **`game_node`**: Men-subscribe topik gambar mentah, melakukan segmentasi warna HSV dan pemrosesan morfologi untuk mendeteksi objek pemain, memperbarui fisika pergerakan bola virtual berdasarkan *timestamp* waktu nyata (dt), lalu mempublikasikan skor ke `/game/score` (`std_msgs/msg/Int32`) dan hasil visualisasi ke `/game/debug_image` (`sensor_msgs/msg/Image`).


### Tabel Topik ROS2
| Topik | Tipe Pesan | Publisher | Subscriber | Keterangan |
| :--- | :--- | :--- | :--- | :--- |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | `camera_node` | `game_node` | Frame mentah dari kamera/video |
| `/game/score` | `std_msgs/Int32` | `game_node` | *(opsional)* | Skor saat ini, dipublikasikan setiap berubah |
| `/game/debug_image` | `sensor_msgs/msg/Image` | `game_node` | `rqt_image_view` | Frame dengan anotasi bola, objek terdeteksi, dan skor |

---

## 3. Struktur Repository Package
Berikut adalah struktur folder package:
```text
├── bouncing_ball_catcher/
│   ├── __init__.py
│   ├── camera_node.py
│   └── game_node.py
├── config/
│   └── params.yaml
├── launch/
│   └── game_launch.py
├── package.xml
└── setup.py
```

---

## 4. Cara Instalasi & Menjalankan (Universal ROS2 Jazzy)

> **Catatan:** Pastikan menggunakan lingkungan terminal ROS2 Jazzy murni tanpa konflik environment luar (tanpa Conda).

1. Letakkan folder package `bouncing_ball_catcher` ke dalam direktori `src` pada *workspace* ROS2 kamu (misalnya `~/ros2_ws/src/`).

2. Buka terminal, aktifkan ROS2 Jazzy, lalu lakukan *build* package menggunakan `colcon`:
```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
colcon build --packages-select bouncing_ball_catcher
source install/setup.bash
```

3. Jalankan kedua node secara bersamaan menggunakan *launch file*:
```bash
ros2 launch bouncing_ball_catcher game_launch.py
```

4. Buka terminal baru untuk melihat antarmuka visual game via `rqt_image_view`:
```bash
source /opt/ros/jazzy/setup.bash
ros2 run rqt_image_view rqt_image_view
```
*(Pilih topik `/game/debug_image` pada menu *dropdown* di pojok kiri atas)*.

---

## 5. Tabel Pengujian Sistem & Demo

| No | Komponen yang Diuji | Perintah Terminal (Command) / Langkah Pengujian | Keterangan / Tujuan Pengujian |
| --- | --- | --- | --- |
| **1** | **Menjalankan Sistem Utama** | `ros2 launch bouncing_ball_catcher game_launch.py` | Menyalakan `camera_node` dan `game_node` secara bersamaan menggunakan file *launch*. |
| **2** | **Menampilkan Visual Game** | `rqt_image_view` (pilih `/game/debug_image`) | Membuka antarmuka visual untuk melihat bola pantul dan skor secara *real-time*. |
| **3** | **Menguji Topik Skor** | `ros2 topic echo /game/score` | Membuktikan skor bertambah secara *real-time* saat tutup botol berhasil menahan bola. |
| **4** | **Menguji Service Reset** | `ros2 service call /game/reset std_srvs/srv/Trigger` | Menguji layanan *service* untuk mereset skor kembali ke angka 0. |
| **5** | **Menguji Parameter Dinamis** | `ros2 param set /game_node ball_speed 180.0`<br><br>`ros2 param set /game_node num_balls 5` | Mengubah kecepatan atau jumlah bola secara langsung saat game berjalan tanpa mematikan program. |
| **6** | **Menampilkan `rqt_graph`** | `rqt_graph` | Memunculkan grafik visual hubungan antar node dan topik ROS2 untuk laporan. |

---

