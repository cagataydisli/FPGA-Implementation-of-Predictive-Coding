# Gerekli kütüphaneleri içe aktar
import matplotlib
matplotlib.use('Qt5Agg')

from brian2 import *
import matplotlib.pyplot as plt
import numpy as np
import time
import os


# ======================================================================
# BÖLÜM 1: GÖRSELLEŞTİRME VE YARDIMCI FONKSİYONLAR
# ======================================================================
def plot_layer_activity(fig, grid_spec, layer_monitors, input_data=None, title_prefix="", input_title="Girdi"):
    state_mon, spike_mon = layer_monitors[0], layer_monitors[1]
    rate_mon = layer_monitors[2] if len(layer_monitors) > 2 else None
    num_base_rows = 3
    height_ratios_base = [2, 2, 3]
    if rate_mon:
        num_base_rows += 1
        height_ratios_base = [2, 2, 2, 3]
    num_rows = num_base_rows + 1 if input_data is not None else num_base_rows
    height_ratios = height_ratios_base + [3] if input_data is not None else height_ratios_base
    subgrid = grid_spec.subgridspec(num_rows, 1, hspace=0.15, height_ratios=height_ratios)
    ax_v = fig.add_subplot(subgrid[0, 0])
    ax_isyn = fig.add_subplot(subgrid[1, 0], sharex=ax_v)
    current_row = 2
    ax_rate = None
    if rate_mon:
        ax_rate = fig.add_subplot(subgrid[current_row, 0], sharex=ax_v)
        current_row += 1
    ax_raster = fig.add_subplot(subgrid[current_row, 0], sharex=ax_v)
    current_row += 1
    ax_v.set_title(title_prefix, fontsize=14, pad=15)
    if state_mon and len(state_mon.t) > 0:
        ax_v.plot(state_mon.t / ms, state_mon.v.T / mV, lw=1)
        ax_isyn.plot(state_mon.t / ms, state_mon.I_syn.T / mV, lw=1)
    if rate_mon and len(rate_mon.t) > 0:
        ax_rate.plot(rate_mon.t / ms, rate_mon.rate / Hz, lw=1.5, color='darkorange')
    ax_raster.plot(spike_mon.t / ms, spike_mon.i, '.k', ms=3)
    ax_v.set_ylabel('Potansiyel\n(mV)')
    ax_isyn.set_ylabel('Akım\n(I_syn)')
    if ax_rate:
        ax_rate.set_ylabel('Ateşleme Oranı\n(Hz)')
        ax_rate.grid(True, linestyle='--', alpha=0.6)
    ax_raster.set_ylabel('Nöron\nİndeksi')
    plt.setp(ax_v.get_xticklabels(), visible=False)
    plt.setp(ax_isyn.get_xticklabels(), visible=False)
    if ax_rate:
        plt.setp(ax_rate.get_xticklabels(), visible=False)
    if input_data is not None:
        ax_input = fig.add_subplot(subgrid[current_row, 0], sharex=ax_v)
        if hasattr(input_data, 't'):
            t_in, i_in = input_data.t, input_data.i
        else:
            t_in, i_in = input_data
        if len(t_in) > 0:
            ax_input.plot(t_in / ms, i_in, '.k', ms=3)
        ax_input.set_ylabel(input_title)
        ax_input.set_xlabel('Zaman (ms)')
        plt.setp(ax_raster.get_xticklabels(), visible=False)
    else:
        ax_raster.set_xlabel('Zaman (ms)')


def visualise_connectivity(S):
    Ns, Nt = len(S.source), len(S.target)
    plt.figure(figsize=(10, 4));
    plt.subplot(121)
    plt.plot(zeros(Ns), arange(Ns), 'ok', ms=10);
    plt.plot(ones(Nt), arange(Nt), 'ok', ms=10)
    for i, j in zip(S.i, S.j): plt.plot([0, 1], [i, j], '-k')
    plt.xticks([0, 1], [f'Kaynak ({S.source.name})', f'Hedef ({S.target.name})'])
    plt.ylabel('Nöron indeksi');
    plt.xlim(-0.1, 1.1);
    plt.ylim(-1, max(Ns, Nt))
    plt.subplot(122);
    plt.plot(S.i, S.j, 'ok');
    plt.xlim(-1, Ns);
    plt.ylim(-1, Nt)
    plt.xlabel('Kaynak nöron indeksi');
    plt.ylabel('Hedef nöron indeksi')
    plt.suptitle(f'{S.name} Bağlantı Yapısı')


def plot_memory_activity(mem_A_mon, mem_B_mon):
    """Bellek modülleri A ve B'nin ateşleme aktivitelerini çizer."""
    plt.figure(figsize=(16, 8));
    plt.suptitle("Bellek Modülleri Aktivitesi", fontsize=16)
    ax1 = plt.subplot(2, 1, 1);
    ax1.set_title("Bellek Modülü A - Lineer Dalga")
    ax1.plot(mem_A_mon.t / ms, mem_A_mon.i, '.k', ms=2)
    ax1.set_ylabel("E Nöron İndeksi");
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax2 = plt.subplot(2, 1, 2, sharex=ax1);
    ax2.set_title("Bellek Modülü B - Lineer Dalga")
    ax2.plot(mem_B_mon.t / ms, mem_B_mon.i, '.k', ms=2)
    ax2.set_ylabel("E Nöron İndeksi");
    ax2.set_xlabel("Zaman (ms)");
    ax2.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout(rect=[0, 0, 1, 0.96])


def plot_weight_statistics(weight_stats):
    """
    Tüm 4 plastik sinaps grubunun ağırlık istatistiklerinin
    (ortalama, min, max) zamanla değişimini çizer. BU VERSİYON max(w) İÇERİR.
    """
    fig, (ax_a, ax_b) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
    fig.suptitle("Tüm Plastik Sinapsların Ağırlık İstatistiklerinin Değişimi", fontsize=16)

    # P_A Katmanına Gelen Bağlantılar
    ax_a.set_title("Tahmin Katmanı A'ya (P_A) Gelen Ağırlıklar")
    # A->A bağlantısı
    ax_a.plot(weight_stats['A_A']['t'], weight_stats['A_A']['mean'], lw=2, color='royalblue',
              label='Ort. Ağırlık (A -> A)')
    ax_a.plot(weight_stats['A_A']['t'], weight_stats['A_A']['max'], lw=1.5, color='darkblue', linestyle=':',
              label='Maks. Ağırlık (A -> A)')  # EKLENDİ
    ax_a.fill_between(weight_stats['A_A']['t'], weight_stats['A_A']['min'], weight_stats['A_A']['max'],
                      color='royalblue', alpha=0.2)
    # B->A bağlantısı (çapraz)
    ax_a.plot(weight_stats['B_A']['t'], weight_stats['B_A']['mean'], lw=2, color='darkorange', linestyle='--',
              label='Ort. Ağırlık (B -> A)')
    ax_a.plot(weight_stats['B_A']['t'], weight_stats['B_A']['max'], lw=1.5, color='saddlebrown', linestyle=':',
              label='Maks. Ağırlık (B -> A)')  # EKLENDİ
    ax_a.set_ylabel("Sinaptik Ağırlık (w)")
    ax_a.grid(True, linestyle='--', alpha=0.6)
    ax_a.legend()

    # P_B Katmanına Gelen Bağlantılar
    ax_b.set_title("Tahmin Katmanı B'ye (P_B) Gelen Ağırlıklar")
    # B->B bağlantısı
    ax_b.plot(weight_stats['B_B']['t'], weight_stats['B_B']['mean'], lw=2, color='crimson',
              label='Ort. Ağırlık (B -> B)')
    ax_b.plot(weight_stats['B_B']['t'], weight_stats['B_B']['max'], lw=1.5, color='darkred', linestyle=':',
              label='Maks. Ağırlık (B -> B)')  # EKLENDİ
    ax_b.fill_between(weight_stats['B_B']['t'], weight_stats['B_B']['min'], weight_stats['B_B']['max'], color='crimson',
                      alpha=0.2)
    # A->B bağlantısı (çapraz)
    ax_b.plot(weight_stats['A_B']['t'], weight_stats['A_B']['mean'], lw=2, color='mediumseagreen', linestyle='--',
              label='Ort. Ağırlık (A -> B)')
    ax_b.plot(weight_stats['A_B']['t'], weight_stats['A_B']['max'], lw=1.5, color='purple', linestyle=':',
              label='Maks. Ağırlık (A -> B)')  # EKLENDİ
    ax_b.set_xlabel("Zaman (ms)")
    ax_b.set_ylabel("Sinaptik Ağırlık (w)")
    ax_b.grid(True, linestyle='--', alpha=0.6)
    ax_b.legend()

    plt.tight_layout(rect=[0, 0, 1, 0.96])


def plot_weight_heatmap(syn_obj, initial_weights, col_id, N_E_MEM, N_EXC):
    """Belirli bir sinaps grubunun başlangıç ve bitiş ağırlık matrislerini ısı haritası olarak çizer."""
    w_max_val = syn_obj.w_max[0]
    final_weights = np.copy(syn_obj.w[:])
    initial_w_matrix = np.full((N_E_MEM, N_EXC), np.nan)
    initial_w_matrix[syn_obj.i, syn_obj.j] = initial_weights
    final_w_matrix = np.full((N_E_MEM, N_EXC), np.nan)
    final_w_matrix[syn_obj.i, syn_obj.j] = final_weights
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
    fig.suptitle(f"Bellek {col_id} -> Tahmin {col_id} Bağlantı Ağırlıklarının Öğrenme Haritası", fontsize=18)
    im1 = ax1.imshow(initial_w_matrix, cmap='viridis', aspect='auto', interpolation='none', origin='lower', vmin=0,
                     vmax=w_max_val)
    ax1.set_title("Başlangıç Ağırlıkları");
    ax1.set_xlabel("Hedef: P Nöron İndeksi");
    ax1.set_ylabel("Kaynak: E_chain Nöron İndeksi")
    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
    im2 = ax2.imshow(final_w_matrix, cmap='viridis', aspect='auto', interpolation='none', origin='lower', vmin=0,
                     vmax=w_max_val)
    ax2.set_title("Son Ağırlıklar (Öğrenmeden Sonra)");
    ax2.set_xlabel("Hedef: P Nöron İndeksi")
    fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])


def plot_example_synapses(syn_monitor, syn_obj, initial_weights, final_weights,
                          title_suffix, color,
                          threshold=None, top_k=8, rng_seed=42):
    """
    Her durumda çizim yapar:
    - threshold None ise adaptif belirler (std/percentile tabanlı)
    - güçlenen/zayıflayan yoksa |Δw| en büyük olanlara fallback yapar
    - en az iki örnek (en çok değişen pozitif/proksi-pozitif ve negatif/proksi-negatif) çizer
    """
    import numpy as np
    import matplotlib.pyplot as plt

    print(f">>> Öğrenme kanıtı analizi çiziliyor: {title_suffix}")

    # Güvenlik: şekiller
    w_hist = np.array(syn_monitor.w)  # (nsyn, nt)
    t_hist = np.array(syn_monitor.t) / ms
    if w_hist.ndim == 1:
        # tek sinaps kaydedilmişse (nsyn=1), 2D'ye çevir
        w_hist = w_hist[None, :]

    init = np.asarray(initial_weights).ravel()
    fin  = np.asarray(final_weights).ravel()
    nrec, nt = w_hist.shape
    nvec = min(len(init), len(fin), nrec)
    w_hist = w_hist[:nvec, :]
    init   = init[:nvec]
    fin    = fin[:nvec]

    delta = fin - init

    # Adaptif eşik (eldeki değişime göre otomatik)
    if threshold is None:
        # std çok küçükse 0.001'e sabitle
        thr_std = 0.25 * np.std(delta)     # esnek
        thr_pct = 0.5  * np.percentile(np.abs(delta), 90)  # kuyruklara duyarlı
        threshold = max(0.001, thr_std, thr_pct)

    pos_idx = np.where(delta >  threshold)[0]
    neg_idx = np.where(delta < -threshold)[0]

    rng = np.random.default_rng(rng_seed)

    # Fallback 1: hiç pozitif yoksa "en az zayıflayan"ı pozitif-proksi say
    if len(pos_idx) == 0:
        pos_idx = np.array([int(np.argmax(delta))])  # en "iyi" değişen
    # Fallback 2: hiç negatif yoksa "en çok zayıflayan"ı negatif-proksi say
    if len(neg_idx) == 0:
        neg_idx = np.array([int(np.argmin(delta))])

    # Çok örnek istersen top_k'yı kullanabilirsin; burada 1'er tane örnekle çiziyoruz
    ex_pos = int(rng.choice(pos_idx))
    ex_neg = int(rng.choice(neg_idx))

    # Kaynak/hedef indeksleri (monitor->synapse index hizalı olmalı)
    try:
        src_pos, tgt_pos = int(syn_obj.i[ex_pos]), int(syn_obj.j[ex_pos])
    except Exception:
        src_pos, tgt_pos = -1, -1
    try:
        src_neg, tgt_neg = int(syn_obj.i[ex_neg]), int(syn_obj.j[ex_neg])
    except Exception:
        src_neg, tgt_neg = -1, -1

    # Çizim
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    fig.suptitle(f"Örnek Sinaps Değişimleri - {title_suffix}", fontsize=16)

    strong_hist = w_hist[ex_pos, :]
    weak_hist   = w_hist[ex_neg, :]

    ax1.plot(t_hist, strong_hist, color=color, lw=2.5,
             label=f'Δw: {init[ex_pos]:.3f} → {fin[ex_pos]:.3f}')
    ax1.set_title(f"GÜÇLENEN/EN AZ ZAYIFLAYAN Örnek (i={src_pos}, j={tgt_pos})")
    ax1.set_ylabel("Sinaptik Ağırlık (w)")
    ax1.grid(True, linestyle='--', alpha=0.7); ax1.legend()

    ax2.plot(t_hist, weak_hist, color='dimgray', lw=2.5,
             label=f'Δw: {init[ex_neg]:.3f} → {fin[ex_neg]:.3f}')
    ax2.set_title(f"ZAYIFLAYAN/EN ÇOK ZAYIFLAYAN Örnek (i={src_neg}, j={tgt_neg})")
    ax2.set_xlabel("Zaman (ms)"); ax2.set_ylabel("Sinaptik Ağırlık (w)")
    ax2.grid(True, linestyle='--', alpha=0.7); ax2.legend()

    plt.tight_layout(rect=[0, 0, 1, 0.96])



# YENİ FONKSİYON 1
def analyze_weight_changes(initial_weights, final_weights, col_id, threshold=0.1):
    """
    Başlangıç ve bitiş ağırlıklarını karşılaştırarak kaç sinapsın güçlendiğini,
    zayıfladığını veya değişmediğini sayar ve raporlar.
    """
    valid_indices = np.isfinite(initial_weights) & np.isfinite(final_weights)
    initial_weights = initial_weights[valid_indices]
    final_weights = final_weights[valid_indices]

    total_synapses = len(initial_weights)
    if total_synapses == 0:
        print(f"Kolon {col_id} için analiz edilecek geçerli sinaps bulunamadı.")
        return

    change = final_weights - initial_weights

    strengthened = np.sum(change > threshold)
    weakened = np.sum(change < -threshold)
    unchanged = total_synapses - strengthened - weakened

    initial_mean = np.mean(initial_weights)
    final_mean = np.mean(final_weights)

    print(f"\n--- KOLON {col_id} AĞIRLIK DEĞİŞİM ANALİZİ ---")
    print(f"Toplam Geçerli Sinaps Sayısı: {total_synapses}")
    print(f"Güçlenen Sinapslar (> +{threshold}): {strengthened} ({strengthened / total_synapses:.1%})")
    print(f"Zayıflayan Sinapslar (< -{threshold}): {weakened} ({weakened / total_synapses:.1%})")
    print(f"Belirgin Değişmeyen Sinapslar: {unchanged} ({unchanged / total_synapses:.1%})")
    print(f"Ortalama Ağırlık Değişimi: {initial_mean:.3f} -> {final_mean:.3f}")
    print("-" * (36 + len(col_id)))


def plot_weight_distribution(syn_objects_list, labels_list, w_max):
    """
    Eğitim sonrası tüm plastik sinaps gruplarının ağırlık dağılımını
    histogram olarak çizer.
    """
    num_syn_groups = len(syn_objects_list)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharey=True)
    fig.suptitle('Eğitim Sonu Sinaptik Ağırlık Dağılımı (Histogram)', fontsize=16)

    colors = ['royalblue', 'crimson', 'mediumseagreen', 'darkorange']

    # Eksenleri düz bir listeye çevirerek kolayca döngüye al
    flat_axes = axes.flatten()

    for i, syn_obj in enumerate(syn_objects_list):
        ax = flat_axes[i]
        weights = syn_obj.w[:]
        weights = weights[np.isfinite(weights)]  # NaN kontrolü

        ax.hist(weights, bins=50, range=(0, w_max), color=colors[i], alpha=0.8)
        ax.set_title(f'Ağırlıklar: {labels_list[i]}')
        ax.set_xlabel('Sinaptik Ağırlık (w)')
        ax.grid(True, linestyle='--', alpha=0.6)

        # Sadece sol sütundaki grafiklere Y ekseni etiketi koy
        if i % 2 == 0:
            ax.set_ylabel('Sinaps Sayısı')

    plt.tight_layout(rect=[0, 0, 1, 0.95])


def print_simulation_summary(spike_monitors, final_weights, N_input_per_tone):
    """
    Simülasyon sonunda istenen formatta genel bir özeti yazdırır.
    Artık tüm 4 plastik bağlantı grubunu da gösterir.
    """
    print("\n" + "=" * 50)
    print(" " * 12 + "SİMÜLASYON SONU ÖZETİ")
    print("=" * 50)

    # --- ÖĞRENME SONRASI AĞIRLIK İSTATİSTİKLERİ ---
    print("\n--- ÖĞRENME SONRASI AĞIRLIK İSTATİSTİKLERİ ---")
    w_aa = final_weights.get('A_A', np.array([0]))
    w_bb = final_weights.get('B_B', np.array([0]))
    w_ab = final_weights.get('A_B', np.array([0]))  # <-- Yeni veri alınıyor
    w_ba = final_weights.get('B_A', np.array([0]))  # <-- Yeni veri alınıyor

    print(f"Ağırlıklar (A->A): Min={np.min(w_aa):.3f}, Max={np.max(w_aa):.3f}, Ortalama={np.mean(w_aa):.3f}")
    print(f"Ağırlıklar (B->B): Min={np.min(w_bb):.3f}, Max={np.max(w_bb):.3f}, Ortalama={np.mean(w_bb):.3f}")
    print(
        f"Ağırlıklar (A->B): Min={np.min(w_ab):.3f}, Max={np.max(w_ab):.3f}, Ortalama={np.mean(w_ab):.3f}")  # <-- YENİ EKLENEN SATIR
    print(
        f"Ağırlıklar (B->A): Min={np.min(w_ba):.3f}, Max={np.max(w_ba):.3f}, Ortalama={np.mean(w_ba):.3f}")  # <-- YENİ EKLENEN SATIR

    # --- THALAMIC GİRDİ ATEŞLEME SAYILARI ---
    print("\n--- THALAMIC GİRDİ ATEŞLEME SAYILARI ---")
    thalamic_mon = spike_monitors.get('Input Thalamic')
    thalamic_a_count = 0
    thalamic_b_count = 0
    if thalamic_mon:
        thalamic_a_count = np.sum(thalamic_mon.i < N_input_per_tone)
        thalamic_b_count = np.sum(thalamic_mon.i >= N_input_per_tone)
    print(f"Thalamic Girdi A: {thalamic_a_count}")
    print(f"Thalamic Girdi B: {thalamic_b_count}")

    # --- KORTİKAL KOLON ATEŞLEME SAYILARI ---
    print("\n--- KORTİKAL KOLON ATEŞLEME SAYILARI ---")
    mon_pe_a = spike_monitors.get('Column A - PE');
    pe_a = mon_pe_a.num_spikes if mon_pe_a else 0
    mon_p_a = spike_monitors.get('Column A - P');
    p_a = mon_p_a.num_spikes if mon_p_a else 0
    mon_i_a = spike_monitors.get('Column A - I');
    i_a = mon_i_a.num_spikes if mon_i_a else 0
    print(f"Kolon A - PE: {pe_a}, P: {p_a}, I: {i_a}")

    mon_pe_b = spike_monitors.get('Column B - PE');
    pe_b = mon_pe_b.num_spikes if mon_pe_b else 0
    mon_p_b = spike_monitors.get('Column B - P');
    p_b = mon_p_b.num_spikes if mon_p_b else 0
    mon_i_b = spike_monitors.get('Column B - I');
    i_b = mon_i_b.num_spikes if mon_i_b else 0
    print(f"Kolon B - PE: {pe_b}, P: {p_b}, I: {i_b}")

    # --- BELLEK MODÜLÜ ATEŞLEME SAYILARI ---
    print("\n--- BELLEK MODÜLÜ ATEŞLEME SAYILARI ---")
    mon_mem_a = spike_monitors.get('Memory A (E_chain)');
    mem_a = mon_mem_a.num_spikes if mon_mem_a else 0
    mon_mem_b = spike_monitors.get('Memory B (E_chain)');
    mem_b = mon_mem_b.num_spikes if mon_mem_b else 0
    print(f"Bellek A E_chain: {mem_a}")
    print(f"Bellek B E_chain: {mem_b}")
    print("\n" + "=" * 50 + "\n")


# YENİ FONKSİYON 2
def quantify_mmn_response(mon_pe_A, mon_pe_B, tones, times, window_start_ms=0, window_end_ms=150):
    """
    Belirli bir zaman ARALIĞINDAKİ PE nöronu ateşlemelerini sayarak MMN etkisini
    sayısal olarak ölçen GÜNCELLENMİŞ fonksiyon.
    """
    print("\n" + "-" * 50)
    print("--- MMN ETKİSİ SAYISAL ANALİZİ ---")

    t_standard_event = None
    t_deviant_event = None

    # Dizide bir standart sesi (0) hemen bir aykırı sesin (1) takip ettiği ilk örneği bul
    for i in range(len(tones) - 1):
        if tones[i] == 0 and tones[i + 1] == 1:
            t_standard_event = times[i]
            t_deviant_event = times[i + 1]
            print(
                f"Analiz için bulunan çift: Standart (t={t_standard_event / ms:.0f}ms), Aykırı (t={t_deviant_event / ms:.0f}ms)")
            break

    if t_standard_event is None or t_deviant_event is None:
        print("UYARI: Analiz için uygun 'standart tonu takip eden aykırı ton' çifti bulunamadı.")
        print("-" * 50 + "\n")
        return

    # Zaman aralığını, fonksiyonun yeni parametrelerini kullanarak belirle
    start_window = window_start_ms * ms
    end_window = window_end_ms * ms

    # Spike sayımlarını yeni aralığa göre yap
    std_mask = (mon_pe_A.t >= t_standard_event + start_window) & (mon_pe_A.t < t_standard_event + end_window)
    std_spike_count = len(mon_pe_A.t[std_mask])

    dev_mask = (mon_pe_B.t >= t_deviant_event + start_window) & (mon_pe_B.t < t_deviant_event + end_window)
    dev_spike_count = len(mon_pe_B.t[dev_mask])

    # Raporlama metnini yeni aralığa göre güncelle
    print(f"Analiz Penceresi: Uyaran sonrası {window_start_ms} ms ile {window_end_ms} ms arası")
    print(f"Standart Sese Tepki (PE_A Spike Sayısı): {std_spike_count}")
    print(f"Aykırı Sese Tepki (PE_B Spike Sayısı):   {dev_spike_count}")

    if dev_spike_count > std_spike_count:
        print(">>> SONUÇ: MMN etkisi gözlemlendi (Aykırı sese verilen hata tepkisi daha yüksek).")
    else:
        print(">>> SONUÇ: Beklenen MMN etkisi gözlemlenmedi.")
    print("-" * 50 + "\n")


def _as_ms_quantity(x):
    return x if isinstance(x, Quantity) else x * ms


def _pick_AB_after(tones, times, t_min_ms=0, prefer='last'):
    """
    'A (0) -> B (1)' ardışık çifti bul. Dönen değerler: (t_A, t_B)  [ikisi de ms niceliği]
    """
    tones = np.asarray(tones)
    cand = np.where((tones[:-1] == 0) & (tones[1:] == 1))[0]  # B indeksleri - 1
    if len(cand) == 0:
        return None, None
    # A'nın indeksleri cand, B'nin indeksleri cand+1 olacak
    tA_ms = np.array([float(_as_ms_quantity(times[i]) / ms) for i in cand])
    mask = (tA_ms >= t_min_ms)
    cand = cand[mask]
    if len(cand) == 0:
        return None, None
    i = cand[-1] if prefer == 'last' else cand[0]
    return _as_ms_quantity(times[i]), _as_ms_quantity(times[i + 1])


def _find_AB_pairs_after(tones, times, t_min_ms=0, gap_target_ms=200, gap_tol_ms=5):
    """
    t >= t_min_ms sonrası tüm A->B (0->1) çiftlerini döndürür.
    gap_target_ms ± gap_tol_ms koşulunu uygular (ms).
    Dönüş: [(tA_ms, tB_ms), ...]  (Brian2 ms nicelikleri)
    """
    tones = np.asarray(tones)
    idxA = np.where((tones[:-1] == 0) & (tones[1:] == 1))[0]  # A index (B = A+1)
    if len(idxA) == 0:
        return []

    tA_ms = np.array([float(_as_ms_quantity(times[i]) / ms) for i in idxA])
    tB_ms = np.array([float(_as_ms_quantity(times[i + 1]) / ms) for i in idxA])

    m = tA_ms >= t_min_ms
    if gap_target_ms is not None:
        m &= np.abs((tB_ms - tA_ms) - gap_target_ms) <= gap_tol_ms

    idxA = idxA[m]
    if len(idxA) == 0:
        return []

    pairs = [(_as_ms_quantity(times[i]), _as_ms_quantity(times[i + 1])) for i in idxA]
    return pairs


def plot_AB_sequence_window(
        tones, times,
        monitors_A, monitors_B,
        thalamic_spikemon, thalamic_statemon,
        N_input_per_tone,
        pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50,
        t_min_ms=350000, prefer='last'
):
    """
    A (standart) ardından B (aykırı) gelen bir AB çifti için:
    - P ve PE spike rasterları (Kolon A ve Kolon B ayrı sütunlar)
    - Talamik giriş rasterları (A ve B ayrı)
    - Zaman penceresi: A'dan 50ms önce başlar, B'den 50ms sonra biter (varsayılanlar)
    Dönüş: oluşturulan matplotlib Figure nesnesi
    """
    # 1) Uygun AB çifti seç
    tA, tB = _pick_AB_after(tones, times, t_min_ms=t_min_ms, prefer=prefer)
    if tA is None or tB is None:
        print(f"AB çifti bulunamadı (t >= {t_min_ms} ms). Daha erken arıyorum…")
        tA, tB = _pick_AB_after(tones, times, t_min_ms=0, prefer='last')
        if tA is None or tB is None:
            print("Uygun AB çifti yok, çizim atlandı.")
            return None

    # 2) Pencere (mutlak) ve eksen (A'ya göre göreli)
    pre = pre_ms * ms
    stim = stim_ms * ms
    gap = gap_ms * ms
    post = post_ms * ms

    t0_abs = tA - pre
    t1_abs = tB + stim + post

    x0 = -pre_ms
    x_end = float((t1_abs - tA) / ms)

    # 3) Thalamus A/B ayrımı
    th_A = (thalamic_spikemon.t[thalamic_spikemon.i < N_input_per_tone],
            thalamic_spikemon.i[thalamic_spikemon.i < N_input_per_tone])
    th_B = (thalamic_spikemon.t[thalamic_spikemon.i >= N_input_per_tone],
            thalamic_spikemon.i[thalamic_spikemon.i >= N_input_per_tone] - N_input_per_tone)

    # 4) Pencere içi veri çıkarıcı
    def window_spikes(spmon, t0, t1, ref_t):
        if isinstance(spmon, SpikeMonitor):
            t = spmon.t
            i = spmon.i
        else:
            t, i = spmon
        m = (t >= t0) & (t < t1)
        return ((t[m] - ref_t) / ms, i[m])

    # 5) P/PE spikemon’ları
    sm_p_A = monitors_A.get('spikemon_p')
    sm_pe_A = monitors_A.get('spikemon_pe')
    sm_p_B = monitors_B.get('spikemon_p')
    sm_pe_B = monitors_B.get('spikemon_pe')

    # 6) Pencere içi veriler
    pA_t, pA_i = window_spikes(sm_p_A, t0_abs, t1_abs, tA) if sm_p_A is not None else (np.array([]), np.array([]))
    peA_t, peA_i = window_spikes(sm_pe_A, t0_abs, t1_abs, tA) if sm_pe_A is not None else (np.array([]), np.array([]))
    pB_t, pB_i = window_spikes(sm_p_B, t0_abs, t1_abs, tA) if sm_p_B is not None else (np.array([]), np.array([]))
    peB_t, peB_i = window_spikes(sm_pe_B, t0_abs, t1_abs, tA) if sm_pe_B is not None else (np.array([]), np.array([]))
    thA_t, thA_i = window_spikes(th_A, t0_abs, t1_abs, tA)
    thB_t, thB_i = window_spikes(th_B, t0_abs, t1_abs, tA)

    # 7) Konsola bilgi
    tA_ms = float(tA / ms);
    tB_ms = float(tB / ms)
    print(f"[AB penceresi] A @ {tA_ms:.0f} ms, B @ {tB_ms:.0f} ms | pencere = [{x0:.0f}, {x_end:.0f}] ms")
    print(f"P(A) spikes={len(pA_t)},  PE(A) spikes={len(peA_t)}")
    print(f"P(B) spikes={len(pB_t)},  PE(B) spikes={len(peB_t)}")
    print(f"Thalamus A spikes={len(thA_t)}, Thalamus B spikes={len(thB_t)}")

    # 8) Çizim (tek figür — sonunda return edeceğiz)
    fig = plt.figure(figsize=(14, 8))
    fig.suptitle(
        f"AB Denemesi: A @ {int(tA / ms)} ms, B @ {int(tB / ms)} ms  (Δ={int((tB - tA) / ms)} ms)",
        fontsize=15
    )
    grid = fig.add_gridspec(3, 2, hspace=0.5, wspace=0.25, left=0.1, right=0.96)

    panels = [
        ('Predictive (Kolon A)', pA_t, pA_i, (0, 0)),
        ('Predictive (Kolon B)', pB_t, pB_i, (0, 1)),
        ('Prediction Error (Kolon A)', peA_t, peA_i, (1, 0)),
        ('Prediction Error (Kolon B)', peB_t, peB_i, (1, 1)),
        ('Thalamic Input A', thA_t, thA_i, (2, 0)),
        ('Thalamic Input B', thB_t, thB_i, (2, 1)),
    ]

    ref_ax = None
    for title, tt, ii, (r, c) in panels:
        ax = fig.add_subplot(grid[r, c])
        if len(tt) > 0:
            ax.plot(tt, ii, '.k', ms=2)
        ax.set_title(title, pad=8)
        ax.set_xlim(x0, x_end)
        ax.set_ylabel("Nöron indeksi")
        if r == 2:
            ax.set_xlabel("A olayına göre zaman (ms)")
        else:
            ax.tick_params(labelbottom=False)

        # Uyarı bantları ve çizgiler
        ax.axvspan(0, float(stim / ms), color='0.9')
        ax.axvspan(float((tB - tA) / ms), float((tB - tA + stim) / ms), color='0.9')
        ax.axvline(0, color='0.7', linestyle='--', linewidth=1)
        ax.axvline(float((tB - tA) / ms), color='0.7', linestyle='--', linewidth=1)

        if ref_ax is None:
            ref_ax = ax
        else:
            ax.sharex(ref_ax)

        ax.text(0.98, 0.9, f"spikes: {len(tt)}", transform=ax.transAxes,
                ha='right', va='center', fontsize=9)

    # alt bilgi
    fig.text(
        0.5, 0.01,
        f"AB penceresi: pre={pre_ms} ms, stim={stim_ms} ms, gap={gap_ms} ms, post={post_ms} ms",
        ha="center", fontsize=11
    )

    return fig


def plot_AB_sequence_average(
        tones, times,
        monitors_A, monitors_B,
        thalamic_spikemon,
        N_input_per_tone,
        pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50,
        t_min_ms=350000,
        t_max_ms=None,
        gap_tol_ms=10,
        bin_ms=2, smooth_ms=8,
        rate_per_neuron=False,
        **_
):
    print(f"[AB-ortalama] fonksiyona girildi | t_min={t_min_ms}, gap={gap_ms}±{gap_tol_ms}")
    import numpy as np, matplotlib.pyplot as plt
    from brian2 import ms, SpikeMonitor
    from brian2.units.fundamentalunits import Quantity

    # ... (Fonksiyonun başındaki yardımcı fonksiyonlar aynı kalıyor) ...
    def _as_ms(x):
        return x if isinstance(x, Quantity) else x * ms

    def _message_figure(msg, title="A→B Trials Average"):
        fig = plt.figure(figsize=(8, 3), num=title)
        fig.suptitle(title)
        fig.text(0.5, 0.5, msg, ha='center', va='center', fontsize=12)
        return fig

    # ... (A->B çiftlerini toplama kısmı aynı kalıyor) ...
    tones = np.asarray(tones)
    idxA = np.where((tones[:-1] == 0) & (tones[1:] == 1))[0]
    if idxA.size == 0:
        msg = "Hiç A→B çifti yok."
        print("[AB-ortalama]", msg)
        return _message_figure(msg)

    tA = np.array([float(_as_ms(times[i]) / ms) for i in idxA])
    tB = np.array([float(_as_ms(times[i + 1]) / ms) for i in idxA])

    if t_max_ms is None:
        try:
            t_max_ms = float(_as_ms(times[-1]) / ms)
        except Exception:
            t_max_ms = float(tA.max())
    else:
        t_max_ms = float(t_max_ms)

    m = (
            (tA >= float(t_min_ms)) &
            (tA <= t_max_ms) &
            (np.abs((tB - tA) - gap_ms) <= gap_tol_ms)
    )
    idxA = idxA[m]
    if idxA.size == 0:
        msg = f"{t_min_ms}≤t_A≤{t_max_ms} ms & gap≈{gap_ms}±{gap_tol_ms} ms koşulunu sağlayan yok."
        print("[AB-ortalama]", msg)
        return _message_figure(msg)

    pairs = [(_as_ms(times[i]), _as_ms(times[i + 1])) for i in idxA]
    print(f"[AB-ortalama] bulunan çift sayısı: {len(pairs)}")

    # ... (PSTH kurma ve psth/smooth yardımcı fonksiyonları aynı kalıyor) ...
    total = pre_ms + stim_ms + gap_ms + stim_ms + post_ms
    edges = np.arange(-pre_ms, -pre_ms + total + bin_ms, bin_ms)
    centers = edges[:-1] + bin_ms / 2

    sm_p_A = monitors_A.get('spikemon_p');
    sm_pe_A = monitors_A.get('spikemon_pe')
    sm_p_B = monitors_B.get('spikemon_p');
    sm_pe_B = monitors_B.get('spikemon_pe')

    thA = (thalamic_spikemon.t[thalamic_spikemon.i < N_input_per_tone],
           thalamic_spikemon.i[thalamic_spikemon.i < N_input_per_tone])
    thB = (thalamic_spikemon.t[thalamic_spikemon.i >= N_input_per_tone],
           thalamic_spikemon.i[thalamic_spikemon.i >= N_input_per_tone] - N_input_per_tone)

    def psth(spmon):
        if spmon is None:
            return np.zeros(len(edges) - 1)
        if isinstance(spmon, SpikeMonitor):
            t_all = spmon.t;
            Nn = getattr(spmon.source, 'N', 1)
        else:
            t_all = spmon[0];
            Nn = None
        t_ms = np.array([float(tt / ms) for tt in t_all])
        H = np.zeros(len(edges) - 1, dtype=float)
        for tA_q, _ in pairs:
            tA_ms = float(tA_q / ms)
            t0 = tA_ms - pre_ms;
            t1 = t0 + total
            m = (t_ms >= t0) & (t_ms < t1)
            rel = t_ms[m] - tA_ms
            H += np.histogram(rel, bins=edges)[0]
        H = H / len(pairs)
        if rate_per_neuron and isinstance(spmon, SpikeMonitor) and (Nn not in (None, 0)):
            bin_s = bin_ms / 1000.0
            H = (H / bin_s) / max(Nn, 1)
        return H

    def smooth(y, w):
        if w <= 1: return y
        klen = max(1, int(round(w / bin_ms)))
        k = np.ones(klen) / klen
        return np.convolve(y, k, mode='same')

    # ... (Eğrileri oluşturma ve konsola bilgi yazdırma kısmı aynı kalıyor) ...
    P_A, PE_A = smooth(psth(sm_p_A), smooth_ms), smooth(psth(sm_pe_A), smooth_ms)
    P_B, PE_B = smooth(psth(sm_p_B), smooth_ms), smooth(psth(sm_pe_B), smooth_ms)
    TH_A, TH_B = smooth(psth(thA), smooth_ms), smooth(psth(thB), smooth_ms)

    # --- YENİ: Ortak Y-ekseni limitini hesapla ---
    # PE_A ve PE_B eğrilerindeki en yüksek değeri bul
    max_y_pe = 0
    if PE_A is not None and len(PE_A) > 0:
        max_y_pe = max(max_y_pe, np.max(PE_A))
    if PE_B is not None and len(PE_B) > 0:
        max_y_pe = max(max_y_pe, np.max(PE_B))

    # Üstte %10'luk bir boşluk bırak
    ylim_pe = max_y_pe * 1.1 if max_y_pe > 0 else 1.0  # Eğer hiç spike yoksa limit 1 olsun

    # --- çizim ---
    range_str = f"{int(t_min_ms)}–{('end' if t_max_ms is None else int(t_max_ms))} ms"
    fig = plt.figure(figsize=(14, 8), num=f"A→B Trials Average [{range_str}]")
    fig.suptitle(f"A→B denemeleri ortalaması — N={len(pairs)}")
    gs = fig.add_gridspec(3, 2, hspace=0.5, wspace=0.25, left=0.1, right=0.96)

    panels = [
        ('Predictive (A)', centers, P_A, (0, 0)),
        ('Predictive (B)', centers, P_B, (0, 1)),
        ('Prediction Error (A)', centers, PE_A, (1, 0)),
        ('Prediction Error (B)', centers, PE_B, (1, 1)),
        ('Thalamic A', centers, TH_A, (2, 0)),
        ('Thalamic B', centers, TH_B, (2, 1)),
    ]

    ref = None
    for title, x, y, (r, c) in panels:
        ax = fig.add_subplot(gs[r, c])
        ax.plot(x, y, 'k', lw=1.2)
        ax.set_title(title)

        # --- YENİ: Eğer grafik Prediction Error ise, ortak Y limitini ayarla ---
        if title.startswith('Prediction Error'):
            ax.set_ylim(0, ylim_pe)

        ax.set_xlim(-pre_ms, -pre_ms + total)
        ax.axvspan(0, stim_ms, color='0.9')
        ax.axvspan(gap_ms, gap_ms + stim_ms, color='0.9')
        ax.axvline(0, color='0.7', ls='--')
        ax.axvline(gap_ms, color='0.7', ls='--')

        if r == 2:
            ax.set_xlabel("A olayına göre zaman (ms)")
        else:
            ax.tick_params(labelbottom=False)

        ax.set_ylabel("Ort. spike/bin" + (" (Hz/nöron)" if rate_per_neuron else " (deneme başına)"))

        if ref is None:
            ref = ax
        else:
            ax.sharex(ref)

    return fig


def select_mmn_pair(tones, times, *, exclude_first=200, standard_tone=0, deviant_tone=1,
                    min_tail_ms=150, sim_end=None):
    """
    Sonlara yakın bir AB (A->B) deviant ve hemen öncesindeki AA standartı seç.
    Olay sonrası en az 'min_tail_ms' kuyruk kalmasına dikkat eder.
    Dönüş: (t_std_ms, t_dev_ms)  -- ikisi de Brian2 'ms' niceliğinde.
    """
    tones = np.asarray(tones)
    times = np.asarray(times)

    # AB (A->B) indeksleri
    AB = np.where((tones[:-1] == standard_tone) & (tones[1:] == deviant_tone))[0] + 1
    AB = AB[AB > exclude_first]
    if len(AB) == 0:
        return None, None

    # AA (A->A) indeksleri
    AA = np.where((tones[:-1] == standard_tone) & (tones[1:] == standard_tone))[0] + 1
    AA = AA[AA > exclude_first]

    # sim_end kestir (times/monitörlerden geliyorsa saniye de olabilir)
    if sim_end is None:
        sim_end = _as_ms_quantity(times[-1])  # son olay zamanı
    else:
        sim_end = _as_ms_quantity(sim_end)

    # sondan başa uygun deviant ara
    for dev_idx in AB[::-1]:
        prev_AA = AA[AA < dev_idx]
        if len(prev_AA) == 0:
            continue
        t_dev = _as_ms_quantity(times[dev_idx])
        if t_dev + min_tail_ms * ms <= sim_end:
            t_std = _as_ms_quantity(times[prev_AA[-1]])
            return t_std, t_dev

    # bulunamadıysa en son AB'yi ver (pencere daha sonra kısaltılır)
    t_dev = _as_ms_quantity(times[AB[-1]])
    prev_AA = AA[AA < AB[-1]]
    t_std = _as_ms_quantity(times[prev_AA[-1]]) if len(prev_AA) else None
    return t_std, t_dev


def print_mmn_summary(
        tones, times,
        monitors_A, monitors_B,
        layers=('pe', 'p'),  # 'pe' (Prediction Error), 'p' (Predictive)
        window_ms=(0, 150),  # olay penceresi (kısa tut: 0..150/250 ms)
        baseline_ms=(-50, 0),  # None yaparsan baz çıkarılmaz
        exclude_first=200,  # ilk X tonu analiz dışı (ısınma)
        n_trials=100  # her koşul için son N deneme
):
    """
    Kısa pencere AA (standart) vs AB (aykırı) spike sayımlarını konsola basar.
    monitors_A / monitors_B içinde 'spikemon_pe' ve/veya 'spikemon_p' olmalı.
    """
    # --- 1) AA ve AB indeksleri (A->A ve A->B, deviant sonrası standartları dahil ETMEZ)
    tones = np.asarray(tones);
    times = np.asarray(times)
    AA = np.where((tones[:-1] == 0) & (tones[1:] == 0))[0] + 1
    AB = np.where((tones[:-1] == 0) & (tones[1:] == 1))[0] + 1
    AA = AA[AA > exclude_first]
    AB = AB[AB > exclude_first]

    if len(AA) == 0 or len(AB) == 0:
        print("UYARI: exclude_first sonrasında yeterli AA/AB olayı bulunamadı.")
        return

    AA = AA[-n_trials:]
    AB = AB[-n_trials:]

    w0, w1 = (np.array(window_ms) * ms)
    if baseline_ms is None:
        b0 = b1 = None
    else:
        b0, b1 = (np.array(baseline_ms) * ms)

    def count_in_window(spmon, t_event, a0, a1):
        m = (spmon.t >= (t_event + a0)) & (spmon.t < (t_event + a1))
        return int(np.sum(m))

    def counts_for(spmon, idx_list):
        vals = []
        for idx in idx_list:
            t_ev = times[idx]
            t_ev = _as_ms_quantity(t_ev)
            c = count_in_window(spmon, t_ev, w0, w1)
            if b0 is not None:
                c -= count_in_window(spmon, t_ev, b0, b1)
            vals.append(c)
        return np.array(vals, dtype=float)

    key_for = {'pe': 'spikemon_pe', 'p': 'spikemon_p'}

    hdr = "=== MMN ÖZET (kısa pencere) ==="
    sub = f"pencere=[{window_ms[0]}, {window_ms[1]}] ms | baseline=" + (
        "yok" if baseline_ms is None else f"[{baseline_ms[0]}, {baseline_ms[1]}] ms")
    info = f"exclude_first={exclude_first}, AA_n={len(AA)}, AB_n={len(AB)}"
    print(hdr);
    print(sub);
    print(info)

    for lyr in layers:
        sm_key = key_for.get(lyr)
        smA = monitors_A.get(sm_key) if sm_key else None
        smB = monitors_B.get(sm_key) if sm_key else None
        if smA is None or smB is None:
            print(f"- {lyr.upper()}: '{sm_key}' bulunamadı, atlanıyor.")
            continue

        AA_counts = counts_for(smA, AA)  # Standart (AA) → A bloğu
        AB_counts = counts_for(smB, AB)  # Aykırı  (AB) → B bloğu

        mu_AA, sd_AA = float(np.mean(AA_counts)), float(np.std(AA_counts, ddof=1) if len(AA_counts) > 1 else 0.0)
        mu_AB, sd_AB = float(np.mean(AB_counts)), float(np.std(AB_counts, ddof=1) if len(AB_counts) > 1 else 0.0)
        # Cohen's d (bağımsız örneklem)
        if len(AA_counts) > 1 and len(AB_counts) > 1:
            pooled = np.sqrt(((len(AA_counts) - 1) * sd_AA ** 2 + (len(AB_counts) - 1) * sd_AB ** 2) / (
                    len(AA_counts) + len(AB_counts) - 2))
            d = (mu_AB - mu_AA) / pooled if pooled > 0 else np.nan
        else:
            d = np.nan

        print(f"\n[{lyr.upper()}]")
        print(f"AA mean±sd  : {mu_AA:.2f} ± {sd_AA:.2f}")
        print(f"AB mean±sd  : {mu_AB:.2f} ± {sd_AB:.2f}")
        print(f"Fark (AB-AA): {mu_AB - mu_AA:.2f}")
        print(f"Cohen's d   : {d:.2f}")


# GÜNCELLENMİŞ FONKSİYON
def create_mmn_comparison_plot(
        tones, times,
        monitors_A, monitors_B,
        thalamic_spikemon, thalamic_statemon,
        memory_module_A, memory_module_B,
        N_input_per_tone,
        window_start_ms=0, window_end_ms=2000,
        sim_end=None
):
    """
    Standart (A) ve aykırı (B) uyarana verilen tepkileri (4 katman) olay-hizalı karşılaştırır.
    Erken-kesilme yaşamamak için, mümkünse 'deviant' olayından sonra pencereyi (varsayılan 2000 ms)
    bütünüyle sığdırabilecek ilk A->B çiftini seçer. Aksi halde pencereyi simülasyon sonuna göre kısaltır.

    Parametreler:
      - window_start_ms, window_end_ms: Olay sonrası çizilecek pencere (ms)
      - sim_end: Simülasyon bitiş zamanı (brian2 zaman birimi). None ise monitörlerden kestirilir.
    """
    print(">>> MMN Karşılaştırma Grafiği (Tüm Katmanlar) oluşturuluyor...")

    # --- 0) Pencere ve yardımcılar
    time_window = np.array([window_start_ms, window_end_ms]) * ms

    def _estimate_sim_end():
        # Monitörlerden ve 'times' dizisinden en son zamanı topla
        candidates = []
        try:
            if len(times) > 0: candidates.append(times[-1])
        except Exception:
            pass

        def push_t(mon):
            try:
                if mon is None: return
                if hasattr(mon, "t") and len(mon.t) > 0:
                    candidates.append(mon.t[-1])
            except Exception:
                pass

        # Thalamus
        push_t(thalamic_spikemon)
        push_t(thalamic_statemon)

        # Diğer bütün monitörler (A/B + bellek modülleri)
        for dct in (monitors_A, monitors_B, memory_module_A, memory_module_B):
            for mon in dct.values():
                if isinstance(mon, (SpikeMonitor, StateMonitor)):
                    push_t(mon)
                elif isinstance(mon, tuple) and len(mon) == 2:
                    t_all, _ = mon
                    try:
                        if len(t_all) > 0:
                            candidates.append(t_all[-1])
                    except Exception:
                        pass

        return max(candidates) if len(candidates) else (window_end_ms * ms)

    sim_end = _estimate_sim_end() if sim_end is None else sim_end

    # --- 1) Uygun standart->aykırı olay çifti seçimi
    standard_indices = np.where(tones == 0)[0]
    deviant_indices = np.where(tones == 1)[0]

    if len(standard_indices) == 0 or len(deviant_indices) == 0:
        print("UYARI: Dizide standart veya aykırı ses yok. MMN grafiği atlanıyor.")
        return

    tail = time_window[1] - time_window[0]
    pair = None
    for dev_idx in deviant_indices:  # sondan değil, baştan tara
        preceding = standard_indices[standard_indices < dev_idx]
        if len(preceding) == 0:
            continue
        t_dev = times[dev_idx]
        if t_dev + tail <= sim_end:  # pencere sığıyorsa ilk uygun çifti seç
            pair = (preceding[-1], dev_idx)
            break

    # Hiçbiri sığmıyorsa: son uygun çifte düş ve pencereyi kısalt
    shortened = False
    if pair is None:
        for dev_idx in deviant_indices[::-1]:
            preceding = standard_indices[standard_indices < dev_idx]
            if len(preceding) == 0:
                continue
            pair = (preceding[-1], dev_idx)
            # deviant sonuna kalan süre kadar kısalt
            avail = max(sim_end - times[dev_idx], 0 * ms)
            if avail < tail:
                time_window[1] = avail
                shortened = True
            break

    if pair is None:
        print("UYARI: Kendisinden önce standart olan bir aykırı bulunamadı. MMN grafiği atlanıyor.")
        return

    std_idx, dev_idx = pair
    t_standard_event = times[std_idx]
    t_deviant_event = times[dev_idx]

    avail_std = max(sim_end - t_standard_event, 0 * ms)
    avail_dev = max(sim_end - t_deviant_event, 0 * ms)
    final_xlim_end = min(time_window[1], avail_std, avail_dev)

    print(f"Seçilen çift: Standart t={t_standard_event / ms:.0f} ms, Aykırı t={t_deviant_event / ms:.0f} ms")
    print(f"Simülasyon sonu t={sim_end / ms:.0f} ms | "
          f"Std-sonrası eldeki süre={avail_std / ms:.0f} ms, Dev-sonrası eldeki süre={avail_dev / ms:.0f} ms")
    if shortened or final_xlim_end < time_window[1]:
        print(
            f"Not: Pencere {window_end_ms} ms yerine {final_xlim_end / ms:.0f} ms olarak çizilecek (kuyruk yetersiz).")

    # --- 2) Pencere içi veri çıkarıcı
    def get_windowed_data(monitor, t_event):
        if monitor is None:
            return (None, None)
        t_start = t_event + time_window[0]
        t_end = t_event + time_window[1]
        t_end = min(t_end, sim_end)  # güvenli kırpma

        if isinstance(monitor, SpikeMonitor):
            mask = (monitor.t >= t_start) & (monitor.t < t_end)
            return (monitor.t[mask] - t_event) / ms, monitor.i[mask]
        elif isinstance(monitor, StateMonitor):
            mask = (monitor.t >= t_start) & (monitor.t < t_end)
            if not np.any(mask):
                return np.array([]), np.array([])
            valid_slice = monitor.v[:, mask]
            if valid_slice.shape[1] == 0:
                return np.array([]), np.array([])
            return (monitor.t[mask] - t_event) / ms, np.nanmean(valid_slice / mV, axis=0)
        elif isinstance(monitor, tuple):
            # thalamik spike'ları (t, i) olarak geçiyoruz
            t_all, i_all = monitor
            mask = (t_all >= t_start) & (t_all < t_end)
            return (t_all[mask] - t_event) / ms, i_all[mask]
        return (None, None)

    # --- 3) Veri kaynaklarını hazırla (A/B + bellek + thalamus)
    thalamic_A_spikes = (
        thalamic_spikemon.t[thalamic_spikemon.i < N_input_per_tone],
        thalamic_spikemon.i[thalamic_spikemon.i < N_input_per_tone]
    )
    thalamic_B_spikes = (
        thalamic_spikemon.t[thalamic_spikemon.i >= N_input_per_tone],
        thalamic_spikemon.i[thalamic_spikemon.i >= N_input_per_tone] - N_input_per_tone
    )

    all_mons_A = {**monitors_A, **memory_module_A,
                  'thalamic_statemon': thalamic_statemon,
                  'thalamic_spikemon': thalamic_A_spikes}
    all_mons_B = {**monitors_B, **memory_module_B,
                  'thalamic_statemon': thalamic_statemon,
                  'thalamic_spikemon': thalamic_B_spikes}

    layers = [
        {'title': 'Memory trace', 'spikes': 'spikemon_mem_e', 'vm': 'statemon_mem_e'},
        {'title': 'Predictive Layer', 'spikes': 'spikemon_p', 'vm': 'statemon_p'},
        {'title': 'Prediction Error Layer', 'spikes': 'spikemon_pe', 'vm': 'statemon_pe'},
        {'title': 'Thalamic Input', 'spikes': 'thalamic_spikemon', 'vm': 'thalamic_statemon'}
    ]

    # --- 4) Pencere verilerini topla
    data = {'standard': {}, 'deviant': {}}
    for condition, event_time, src in [
        ('standard', t_standard_event, all_mons_A),
        ('deviant', t_deviant_event, all_mons_B),
    ]:
        for layer in layers:
            data[condition][layer['spikes']] = get_windowed_data(src.get(layer['spikes']), event_time)
            data[condition][layer['vm']] = get_windowed_data(src.get(layer['vm']), event_time)

    # --- 5) Çizim
    fig = plt.figure(figsize=(14, 14))
    fig.suptitle("Standart ve Aykırı Sese Verilen Nöral Tepkilerin Karşılaştırılması (MMN Etkisi)", fontsize=16)

    main_grid = fig.add_gridspec(4, 2, hspace=0.7, wspace=0.25, left=0.15, right=0.95)
    ref_ax = None

    for col_idx, condition in enumerate(['standard', 'deviant']):
        for row_idx, layer_info in enumerate(layers):
            inner_grid = main_grid[row_idx, col_idx].subgridspec(2, 1, hspace=0.1, height_ratios=[2, 1.5])
            ax_raster = fig.add_subplot(inner_grid[0, 0])
            ax_vm = fig.add_subplot(inner_grid[1, 0], sharex=ax_raster)

            t_vm, v_mean = data[condition][layer_info['vm']]
            if t_vm is not None and len(t_vm) > 0:
                ax_vm.plot(t_vm, v_mean, 'k')
            ax_vm.set_ylim(-80, 45)

            t_spk, i_spk = data[condition][layer_info['spikes']]
            if t_spk is not None and len(t_spk) > 0:
                ax_raster.plot(t_spk, i_spk, '.k', ms=2)

            if ref_ax is None:
                ref_ax = ax_raster
            else:
                ax_raster.sharex(ref_ax)

            plt.setp(ax_raster.get_xticklabels(), visible=False)

            if col_idx == 0:
                ax_raster.set_ylabel(f"{layer_info['title']}\n\nNöron Indeksi")
                ax_vm.set_ylabel('Ort. Vm\n(mV)')

            if row_idx == 0:
                ax_raster.set_title("Standart Sese Tepki" if condition == 'standard' else "Aykırı Sese Tepki", pad=15)

            if row_idx == len(layers) - 1:
                ax_vm.set_xlabel("Olay Zamanından İtibaren Zaman (ms)")
            else:
                plt.setp(ax_vm.get_xticklabels(), visible=False)

    if ref_ax is not None:
        # X-limit: iki kolonun da fiilen sahip olduğu pencereye göre
        ref_ax.set_xlim(time_window[0] / ms, final_xlim_end / ms)


def _pick_late_events(tones, times, exclude_first=200):
    """
    Geç dönemden iki olay seçer:
      - std_idx: 'AA' (öncesi de A olan standart)
      - dev_idx: 'AB' (öncesi A olan aykırı B)
    exclude_first: ilk kaç tonu eğitim ısınması sayıp dışarı atalım.
    """
    tones = np.asarray(tones);
    times = np.asarray(times)
    # AB (A->B) deviantlar (indeks B'yi verir)
    dev_indices = np.where((tones[:-1] == 0) & (tones[1:] == 1))[0] + 1
    dev_indices = dev_indices[dev_indices > exclude_first]
    if len(dev_indices) == 0:
        return None, None
    dev_idx = dev_indices[-1]  # sondan al

    # AA (A->A) standartlar (indeks ikinci A'yı verir)
    std_candidates = np.where((tones[1:] == 0) & (tones[:-1] == 0))[0] + 1
    std_candidates = std_candidates[std_candidates > exclude_first]

    # dev_idx'ten önceki en yakın AA'yı al (BA sonrası standartları hariç tutarız)
    std_candidates = std_candidates[std_candidates < dev_idx]
    if len(std_candidates) == 0:
        return None, times[dev_idx]
    std_idx = std_candidates[-1]

    return times[std_idx], times[dev_idx]


def create_mmn_comparison_plot_short(
        tones, times, monitors_A, monitors_B,
        thalamic_spikemon, thalamic_statemon,
        memory_module_A, memory_module_B, N_input_per_tone,
        window_start_ms=-50, window_end_ms=250, exclude_first=200,
        stim_ms=50, gap_ms=200
):
    """
    Kısa pencere MMN karşılaştırması (tek A→B çifti).
    - Çift B'den bulunur (öncesi mutlaka A).
    - İki sütun da aynı A zamanına göre hizalıdır ve aynı 300 ms pencereyi gösterir.
    - Sol: Standart (A-only) → sadece A penceresi [0, stim_ms]
    - Sağ: Aykırı (B)       → sadece B penceresi [gap_ms, gap_ms+stim_ms]
    """
    import numpy as np
    import matplotlib.pyplot as plt
    from brian2 import ms, mV, SpikeMonitor, StateMonitor

    print(">>> MMN Karşılaştırma Grafiği (kısa pencere) ...")

    # ---------- yardımcılar ----------
    def _to_ms(x):
        try:
            return np.asarray(x / ms, dtype=float)
        except Exception:
            return np.asarray(x, dtype=float)

    def get_windowed(monitor, t_event):
        """Seçilen olay etrafındaki pencereyi (A'ya göre) döndür."""
        if monitor is None:
            return (None, None)
        t0, t1 = t_event + window_start_ms * ms, t_event + window_end_ms * ms
        if isinstance(monitor, SpikeMonitor):
            m = (monitor.t >= t0) & (monitor.t < t1)
            return (monitor.t[m] - t_event) / ms, monitor.i[m]
        elif isinstance(monitor, StateMonitor):
            m = (monitor.t >= t0) & (monitor.t < t1)
            if not np.any(m):
                return np.array([]), np.array([])
            return (monitor.t[m] - t_event) / ms, np.nanmean(monitor.v[:, m] / mV, axis=0)
        elif isinstance(monitor, tuple):  # (t,i)
            t_all, i_all = monitor
            m = (t_all >= t0) & (t_all < t1)
            return (t_all[m] - t_event) / ms, i_all[m]
        return (None, None)

    # panel bazında maske (sol=A penceresi, sağ=B penceresi)
    def _mask_A(rel_t):
        return (rel_t >= 0) & (rel_t <= stim_ms)

    def _mask_B(rel_t):
        return (rel_t >= gap_ms) & (rel_t <= gap_ms + stim_ms)

    def _apply_mask(ts, ids, which):
        if ts is None or len(ts) == 0:
            return ts, ids
        m = _mask_A(ts) if which == 'A' else _mask_B(ts)
        return ts[m], ids[m]

    # ---------- TEK A→B çifti seç (B'den bul) ----------
    tones_arr = np.asarray(tones, dtype=int)
    times_ms_all = _to_ms(times)

    start = max(1, int(exclude_first))  # B için en az 1

    # B indeksleri: bir önceki olay A ise (…0 → 1…)
    b_idx = [i for i in range(start, len(tones_arr))
             if (tones_arr[i] == 1 and tones_arr[i - 1] == 0)]

    # Kuyruk yeterliliği: A'dan sonra window_end_ms kadar zaman kalmalı
    b_idx = [i for i in b_idx
             if (times_ms_all[-1] - times_ms_all[i - 1]) >= (window_end_ms - 1e-9)]

    if not b_idx:
        print("Uyarı: A→B çifti bulunamadı; grafik atlandı.")
        return

    iB = b_idx[-1]  # genelde sonda daha stabildir
    iA = iB - 1
    tA = times[iA]
    tB = times[iB]
    tA_ms = float(times_ms_all[iA])
    tB_ms = float(times_ms_all[iB])

    # ---------- veri blokları ----------
    # thalamus A/B ayrımı (indeks aralığına göre)
    th_A = (thalamic_spikemon.t[thalamic_spikemon.i < N_input_per_tone],
            thalamic_spikemon.i[thalamic_spikemon.i < N_input_per_tone])
    th_B = (thalamic_spikemon.t[thalamic_spikemon.i >= N_input_per_tone],
            thalamic_spikemon.i[thalamic_spikemon.i >= N_input_per_tone] - N_input_per_tone)

    all_A = {**monitors_A, **memory_module_A,
             'thalamic_statemon': thalamic_statemon, 'thalamic_spikemon': th_A}
    all_B = {**monitors_B, **memory_module_B,
             'thalamic_statemon': thalamic_statemon, 'thalamic_spikemon': th_B}

    layers = [
        {'title': 'Memory trace', 'spikes': 'spikemon_mem_e', 'vm': 'statemon_mem_e'},
        {'title': 'Ort. Predictive Layer', 'spikes': 'spikemon_p', 'vm': 'statemon_p'},
        {'title': 'Ort. Prediction Error Layer', 'spikes': 'spikemon_pe', 'vm': 'statemon_pe'},
        {'title': 'Ort. Thalamic Input', 'spikes': 'thalamic_spikemon', 'vm': 'thalamic_statemon'}
    ]

    # A'ya göre pencere al; sol=A maskesi, sağ=B maskesi
    def collect(block, *_, **__):
        """
        block: izlenecek monitor sözlüğü
        *_, **__: çağrı sırasında fazladan verilen etiket vb. argümanları sessizce yoksayar
        """
        out = {}
        for L in layers:
            out[L['spikes']] = get_windowed(block.get(L['spikes']), tA)  # TAM pencere
            out[L['vm']] = get_windowed(block.get(L['vm']), tA)  # TAM pencere
        return out

    data_std = collect(all_A, 'A')  # sol: yalnız A penceresi
    data_dev = collect(all_B, 'B')  # sağ: yalnız B penceresi

    # ---------- çizim ----------
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle(f"A @ {int(tA_ms)} ms, B @ {int(tB_ms)} ms  (Δ = {int(tB_ms - tA_ms)} ms)", fontsize=14)

    grid = fig.add_gridspec(4, 2, hspace=0.6, wspace=0.25, left=0.12, right=0.96)
    ref_ax = None
    bottom_axes = [None, None]

    for col, (label, data) in enumerate([('Standart (AA)', data_std), ('Aykırı (AB)', data_dev)]):
        for row, L in enumerate(layers):
            inner = grid[row, col].subgridspec(2, 1, hspace=0.1, height_ratios=[2, 1.6])
            ax_r = fig.add_subplot(inner[0, 0])
            ax_v = fig.add_subplot(inner[1, 0], sharex=ax_r)

            # Vm
            tvm, vv = data[L['vm']]
            if tvm is not None and len(tvm) > 0:
                ax_v.plot(tvm, vv, 'k')
            ax_v.set_ylim(-80, 45)

            # spikes
            ts, ids = data[L['spikes']]
            if ts is not None and len(ts) > 0:
                ax_r.plot(ts, ids, '.k', ms=2)
            if L['spikes'] == 'spikemon_mem_e':
                ax_r.set_ylim(0, 400)
                ax_r.set_yticks([0, 100, 200, 300, 400])  # (opsiyonel)
            # ortak x ekseni
            if ref_ax is None:
                ref_ax = ax_r
            else:
                ax_r.sharex(ref_ax)
            plt.setp(ax_r.get_xticklabels(), visible=False)

            if col == 0:
                ax_r.set_ylabel(f"{L['title']}\n\nNöron İndeksi")
                ax_v.set_ylabel("Ort. Vm\n(mV)")
            if row == 0:
                ax_r.set_title(label, pad=12)
            if row == len(layers) - 1:
                ax_v.set_xlabel("Olaydan itibaren zaman (ms)")
                bottom_axes[col] = ax_v
            else:
                plt.setp(ax_v.get_xticklabels(), visible=False)

            # küçük sayaç yazıları
            if L['spikes'] == 'spikemon_pe' and ts is not None:
                ax_r.text(0.98, 0.85, f"PE spikes: {len(ts)}",
                          transform=ax_r.transAxes, ha='right', va='center', fontsize=9)
            if L['spikes'] == 'spikemon_p' and ts is not None:
                ax_r.text(0.98, 0.85, f"P spikes: {len(ts)}",
                          transform=ax_r.transAxes, ha='right', va='center', fontsize=9)

    # ortak x-limit
    if ref_ax is not None:
        ref_ax.set_xlim([window_start_ms, window_end_ms])

    # üst "Mutlak zaman" ekseni — İKİ SÜTUN DA tA'ya göre
    def attach_abs_axis(ax, anchor_ms):
        ax_top = ax.twiny()
        ax_top.set_xlim(ax.get_xlim())
        ticks = ax.get_xticks()
        ax_top.set_xticks(ticks)
        ax_top.set_xticklabels([f"{tick + anchor_ms:.0f}" for tick in ticks])
        ax_top.set_xlabel("Mutlak zaman (ms)")
        return ax_top

    if bottom_axes[0] is not None:
        attach_abs_axis(bottom_axes[0], tA_ms)
    if bottom_axes[1] is not None:
        attach_abs_axis(bottom_axes[1], tA_ms)  # sağ da aynı ankora bağlı

    # alt bilgi
    fig.text(
        0.5, 0.04,
        f"AB penceresi: pre={window_start_ms} ms, stim={stim_ms} ms, gap={gap_ms} ms, post={window_end_ms - gap_ms - stim_ms} ms",
        ha="center", fontsize=10
    )

    return fig


# BU FONKSİYONU mmn.py DOSYANIZIN İÇİNE, DİĞER GÖRSELLEŞTİRME
# FONKSİYONLARININ YANINA EKLEYEBİLİRSİNİZ.
# mmn.py dosyanızdaki create_interactive_explorer fonksiyonunu
# aşağıdaki kod bloğu ile tamamen değiştirin.




def window_density_1d(spike_times_ms, t0_ms, win_ms=300, bin_ms=10, n_neurons=None):
    """
    spike_times_ms : 1D array (sadece o katmanın spike zamanları, ms)
    t0_ms          : pencere başlangıcı (ms)
    win_ms         : pencere genişliği (ms)
    bin_ms         : bin genişliği (ms)
    n_neurons      : (ops.) normalize etmek için nöron sayısı
    return         : (dens_norm, bin_edges)
    """
    t1_ms = t0_ms + win_ms
    bins = np.arange(t0_ms, t1_ms + bin_ms, bin_ms, dtype=float)
    # Sadece pencere içindeki spike'ları say
    m = (spike_times_ms >= t0_ms) & (spike_times_ms < t1_ms)
    counts, edges = np.histogram(spike_times_ms[m], bins=bins)

    if n_neurons is not None and n_neurons > 0:
        # spike/saniye/nöron ~ (count / (bin_s * N))
        bin_s = bin_ms / 1000.0
        dens = counts / (bin_s * n_neurons)
    else:
        dens = counts.astype(float)

    # 0–1 aralığına normalize (pencere içi)
    dmax = dens.max() if dens.size else 0.0
    dens_norm = dens / (dmax + 1e-12)
    return dens_norm, edges

def create_interactive_explorer(
        total_duration,
        monitors_A, monitors_B,
        thalamic_spikemon, N_input_per_tone,
        memory_module_A, memory_module_B,
        model_params,
        window_width_ms=300
):
    """
    Tüm simülasyon boyunca gezinebilen, slider, butonlar ve anlık spike sayacı
    özelliklerine sahip, dayanıklı ve interaktif bir görselleştirme aracı.
    """
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider, Button
    from brian2 import ms, mV
    # >>> HEAT-STRIP: import (ek)
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    # <<< HEAT-STRIP

    print(">>> İnteraktif Gezgin (Spike Sayaçlı) oluşturuluyor...")

    # --- 1. Veri Hazırlığı ---
    all_data = {}
    sources = {
        'P_A': {'spikes': monitors_A.get('spikemon_p')},
        'PE_A': {'spikes': monitors_A.get('spikemon_pe')},
        'P_B': {'spikes': monitors_B.get('spikemon_p')},
        'PE_B': {'spikes': monitors_B.get('spikemon_pe')},
        'Mem_A': {'spikes': memory_module_A.get('spikemon_mem_e')},
        'Mem_B': {'spikes': memory_module_B.get('spikemon_mem_e')},
    }
    th_A_mask = thalamic_spikemon.i < N_input_per_tone
    th_B_mask = thalamic_spikemon.i >= N_input_per_tone
    sources['Thalamic_A'] = {'spikes': (thalamic_spikemon.t[th_A_mask], thalamic_spikemon.i[th_A_mask])}
    sources['Thalamic_B'] = {
        'spikes': (thalamic_spikemon.t[th_B_mask], thalamic_spikemon.i[th_B_mask] - N_input_per_tone)}

    for name, mons in sources.items():
        spk_mon = mons['spikes']
        t_spk, i_spk = np.array([]), np.array([], dtype=int)
        if spk_mon is not None:
            t_data = spk_mon[0] if isinstance(spk_mon, tuple) else spk_mon.t
            i_data = spk_mon[1] if isinstance(spk_mon, tuple) else spk_mon.i
            t_spk = np.asarray(t_data / ms)
            i_spk = np.asarray(i_data, dtype=int)
        all_data[name] = {'t_spk': t_spk, 'i_spk': i_spk}

    # --- 2. Figür ve Eksenleri Ayarla ---
    fig = plt.figure(figsize=(18, 12))
    axes = {}
    gs = fig.add_gridspec(4, 2, hspace=0.4, wspace=0.15, top=0.92, bottom=0.20)

    axes['Mem_A'] = fig.add_subplot(gs[0, 0]);
    axes['Mem_B'] = fig.add_subplot(gs[0, 1], sharey=axes['Mem_A'])
    axes['P_A'] = fig.add_subplot(gs[1, 0]);
    axes['P_B'] = fig.add_subplot(gs[1, 1], sharey=axes['P_A'])
    axes['PE_A'] = fig.add_subplot(gs[2, 0]);
    axes['PE_B'] = fig.add_subplot(gs[2, 1], sharey=axes['PE_A'])
    axes['Thalamic_A'] = fig.add_subplot(gs[3, 0]);
    axes['Thalamic_B'] = fig.add_subplot(gs[3, 1], sharey=axes['Thalamic_A'])

    # Başlıklar ve Etiketler...
    axes['P_A'].set_title("Predictive Layer (A)");
    axes['P_A'].set_ylabel("Nöron İndeksi")
    axes['P_B'].set_title("Predictive Layer (B)")
    axes['PE_A'].set_title("Prediction Error (A)");
    axes['PE_A'].set_ylabel("Nöron İndeksi")
    axes['PE_B'].set_title("Prediction Error (B)")
    axes['Mem_A'].set_title("Memory Trace (A)");
    axes['Mem_A'].set_ylabel("Nöron İndeksi")
    axes['Mem_B'].set_title("Memory Trace (B)")
    axes['Thalamic_A'].set_title("Thalamic Input (A)");
    axes['Thalamic_A'].set_ylabel("Nöron İndeksi")
    axes['Thalamic_B'].set_title("Thalamic Input (B)")
    axes['Thalamic_A'].set_xlabel("Zaman (ms)");
    axes['Thalamic_B'].set_xlabel("Zaman (ms)")

    # Y Eksen limitleri...
    n_exc = model_params['N_EXC'];
    n_mem = model_params['N_E_MEM'];
    n_thal = N_input_per_tone
    axes['P_A'].set_ylim(-1, n_exc + 1);
    axes['PE_A'].set_ylim(-1, n_exc + 1)
    axes['Mem_A'].set_ylim(-1, n_mem + 1);
    axes['Thalamic_A'].set_ylim(-1, n_thal + 1)

    # Çizim nesneleri...
    plot_objects = {};
    text_objects = {}
    plot_objects['P_A'], = axes['P_A'].plot([], [], '.k', ms=2)
    plot_objects['P_B'], = axes['P_B'].plot([], [], '.k', ms=2)
    plot_objects['PE_A'], = axes['PE_A'].plot([], [], '.k', ms=2)
    plot_objects['PE_B'], = axes['PE_B'].plot([], [], '.k', ms=2)
    plot_objects['Mem_A'], = axes['Mem_A'].plot([], [], '.b', ms=2)
    plot_objects['Mem_B'], = axes['Mem_B'].plot([], [], '.r', ms=2)
    plot_objects['Thalamic_A'], = axes['Thalamic_A'].plot([], [], '.b', ms=3)
    plot_objects['Thalamic_B'], = axes['Thalamic_B'].plot([], [], '.r', ms=3)

    text_objects['PE_A'] = axes['PE_A'].text(0.98, 0.95, '', ha='right', va='top', transform=axes['PE_A'].transAxes,
                                             fontsize=10, color='darkred')
    text_objects['PE_B'] = axes['PE_B'].text(0.98, 0.95, '', ha='right', va='top', transform=axes['PE_B'].transAxes,
                                             fontsize=10, color='darkred')

    for key in ['P_B', 'PE_B', 'Mem_B', 'Thalamic_B']:
        plt.setp(axes[key].get_yticklabels(), visible=False)

    # >>> HEAT-STRIP: Predictive rasterlarının altına şerit eksenleri + ilk imshow
    # A ekseninin altına
    divA = make_axes_locatable(axes['P_A'])
    ax_pred_A_heat = divA.append_axes("bottom", size="10%", pad=0.10, sharex=axes['P_A'])
    ax_pred_A_heat.set_yticks([]); ax_pred_A_heat.set_xticks([])

    # B ekseninin altına
    divB = make_axes_locatable(axes['P_B'])
    ax_pred_B_heat = divB.append_axes("bottom", size="10%", pad=0.10, sharex=axes['P_B'])
    ax_pred_B_heat.set_yticks([]); ax_pred_B_heat.set_xticks([])

    # Şerit çözünürlüğü
    _bin_ms = 10
    _nbins = max(1, int(round(window_width_ms / _bin_ms)))

    # İlk boş görsel (pencere update sırasında doldurulacak)
    zero_strip = np.zeros((1, _nbins), dtype=float)
    im_heat_A = ax_pred_A_heat.imshow(
        zero_strip, aspect="auto",
        extent=[0, window_width_ms, 0, 1],
        vmin=0, vmax=1, cmap="gray_r", origin="lower"
    )
    im_heat_B = ax_pred_B_heat.imshow(
        zero_strip, aspect="auto",
        extent=[0, window_width_ms, 0, 1],
        vmin=0, vmax=1, cmap="gray_r", origin="lower"
    )
    # <<< HEAT-STRIP

    # --- 3. Kaydırma Çubuğu ve Butonlar ---
    ax_slider = fig.add_axes([0.25, 0.1, 0.5, 0.03])
    slider = Slider(ax=ax_slider, label='Zaman (ms)', valmin=0, valmax=(total_duration / ms) - window_width_ms,
                    valinit=0, valstep=10)
    ax_prev = fig.add_axes([0.14, 0.1, 0.1, 0.03]); btn_prev = Button(ax_prev, '◄ 100ms')
    ax_next = fig.add_axes([0.76, 0.1, 0.1, 0.03]); btn_next = Button(ax_next, '100ms ►')

    # >>> HEAT-STRIP: yoğunluk hesaplayıcı (yerel helper)
    def _window_density_norm_0_1(spike_times_ms, t0_ms, win_ms, bin_ms, n_neurons=None):
        t1_ms = t0_ms + win_ms
        bins = np.arange(t0_ms, t1_ms + bin_ms, bin_ms, dtype=float)
        # pencere içi spike'lar
        if spike_times_ms.size == 0:
            counts = np.zeros(len(bins) - 1, dtype=float)
        else:
            m = (spike_times_ms >= t0_ms) & (spike_times_ms < t1_ms)
            counts, _ = np.histogram(spike_times_ms[m], bins=bins)
            counts = counts.astype(float)
        # istersek nöron başına/s (Hz) normalizasyonu — şimdilik ham sayımı 0–1'e ölçekliyoruz
        dmax = counts.max() if counts.size else 0.0
        dens_norm = counts / (dmax + 1e-12)
        return dens_norm, bins
    # <<< HEAT-STRIP

    # --- 4. Güncelleme Fonksiyonu ---
    def update(val):
        start_time = slider.val
        end_time = start_time + window_width_ms

        for name, data in all_data.items():
            mask = (data['t_spk'] >= start_time) & (data['t_spk'] < end_time)
            t_window, i_window = data['t_spk'][mask], data['i_spk'][mask]

            if name in plot_objects:
                plot_objects[name].set_data(t_window, i_window)

            if name in text_objects:
                spike_count = len(t_window)
                text_objects[name].set_text(f'Spikes: {spike_count}')

        # >>> HEAT-STRIP: Predictive A/B için yoğunluk şeritlerini güncelle
        # A
        densA, edgesA = _window_density_norm_0_1(
            all_data['P_A']['t_spk'], start_time, window_width_ms, _bin_ms
        )
        im_heat_A.set_data(densA[None, :])
        im_heat_A.set_extent([edgesA[0], edgesA[-1], 0, 1])

        # B
        densB, edgesB = _window_density_norm_0_1(
            all_data['P_B']['t_spk'], start_time, window_width_ms, _bin_ms
        )
        im_heat_B.set_data(densB[None, :])
        im_heat_B.set_extent([edgesB[0], edgesB[-1], 0, 1])
        # <<< HEAT-STRIP

        for ax in axes.values():
            ax.set_xlim(start_time, end_time)
        fig.suptitle(f"Simülasyon Gezgini | Pencere: {start_time:.0f} ms - {end_time:.0f} ms", fontsize=16)
        fig.canvas.draw_idle()

    slider.on_changed(update)

    def next_step(event):
        slider.set_val(min(slider.val + 100, slider.valmax))

    def prev_step(event):
        slider.set_val(max(slider.val - 100, slider.valmin))

    btn_next.on_clicked(next_step)
    btn_prev.on_clicked(prev_step)

    # --- 5. Başlatma ---
    update(0)

    return fig, slider, btn_prev, btn_next


# mmn.py dosyanızdaki bu fonksiyonu aşağıdaki ile değiştirin.

def create_weight_profile_figure(
        total_duration,
        model_params,
        syn_AA=None, syn_AB=None, syn_BB=None, syn_BA=None,
        wmon_AA=None, wmon_AB=None, wmon_BB=None, wmon_BA=None,
        t_init_ms=0.0
):
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider, Button
    from brian2 import ms

    g = globals()
    if syn_AA is None: syn_AA = g.get('syn_Mem_to_P_A', None)
    if syn_BB is None: syn_BB = g.get('syn_Mem_to_P_B', None)
    if syn_AB is None: syn_AB = g.get('syn_MemA_to_PB', None)
    if syn_BA is None: syn_BA = g.get('syn_MemB_to_P_A', None)

    def _get_wmax(syn):
        if syn is None: return None
        try:
            return float(np.max(np.asarray(syn.w_max)))
        except:
            return None

    def _snapshot_from_wmon(wmon, t_ms):
        if wmon is None or not hasattr(wmon, 't') or not hasattr(wmon, 'w'): return None
        t_arr = np.asarray(wmon.t / ms)
        if t_arr.size == 0: return None
        idx = int(np.argmin(np.abs(t_arr - t_ms)))
        return np.asarray(wmon.w)[:, idx]

    def _mean_w_by_pre(syn, w_values=None, n_pre_expected=None):
        if syn is None: return None
        try:
            pre_idx = np.asarray(syn.i)
        except:
            return None
        if pre_idx.size == 0: return None
        w_vals = np.asarray(syn.w) if w_values is None else np.asarray(w_values)
        n_pre = int(pre_idx.max()) + 1
        if n_pre_expected is not None: n_pre = max(n_pre, int(n_pre_expected))
        sums = np.zeros(n_pre, dtype=float);
        cnts = np.zeros(n_pre, dtype=int)
        np.add.at(sums, pre_idx, w_vals);
        np.add.at(cnts, pre_idx, 1)
        cnts[cnts == 0] = 1
        return sums / cnts

    def _build_profile(syn, wmon, t_ms, n_pre_expected):
        return _mean_w_by_pre(syn, _snapshot_from_wmon(wmon, t_ms), n_pre_expected)

    # --- fig & axes (alt marj geniş) ---
    n_mem = int(model_params.get('N_E_MEM', 400))
    x_idx = np.arange(n_mem)

    # === DEĞİŞİKLİK 1: Grafiklerin alt boşluğunu daha da artır (0.32 -> 0.35) ===
    fig, axes = plt.subplots(
        2, 2, figsize=(14, 8), sharex=True, sharey=True,
        gridspec_kw=dict(left=0.08, right=0.98, top=0.90, bottom=0.35, hspace=0.30, wspace=0.22)
    )
    ax_AA, ax_AB = axes[0, 0], axes[0, 1]
    ax_BB, ax_BA = axes[1, 0], axes[1, 1]

    for ax, title in [(ax_AA, "A → A"), (ax_AB, "A → B"), (ax_BB, "B → B"), (ax_BA, "B → A")]:
        ax.set_title(title);
        ax.set_xlim(0, n_mem - 1)
        if ax in (ax_AA, ax_BB):
            ax.set_ylabel("Mean w")
        if ax in (ax_BB, ax_BA):
            ax.set_xlabel("Memory neuron index")

    line_AA, = ax_AA.plot([], [], lw=1.2)
    line_AB, = ax_AB.plot([], [], lw=1.2)
    line_BB, = ax_BB.plot([], [], lw=1.2)
    line_BA, = ax_BA.plot([], [], lw=1.2)

    wmaxs = [v for v in (_get_wmax(syn_AA), _get_wmax(syn_AB), _get_wmax(syn_BB), _get_wmax(syn_BA)) if v is not None]
    if wmaxs:
        ytop = 1.05 * max(wmaxs)
        for ax in (ax_AA, ax_AB, ax_BB, ax_BA): ax.set_ylim(0, ytop)

    # --- slider & buttons ---
    def _tmax_from_wmons(*wmons):
        ts = []
        for wm in wmons:
            if wm is not None and hasattr(wm, 't') and len(wm.t):
                ts.append(float(np.max(wm.t / ms)))
        return max(ts) if ts else float(total_duration / ms)

    t_max = _tmax_from_wmons(wmon_AA, wmon_AB, wmon_BB, wmon_BA)

    # === DEĞİŞİKLİK 2: Widget'ları dikeyde daha aşağı al (0.10 -> 0.08) ===
    widget_bottom = 0.08
    widget_height = 0.04

    # === DEĞİŞİKLİK 3: Yatay pozisyonları "Time (ms)" etiketine yer açmak için ayarla ===
    # Sol buton: 0.10'dan başla
    ax_prev = fig.add_axes([0.10, widget_bottom, 0.10, widget_height]);
    ax_prev.set_in_layout(False);
    ax_prev.set_zorder(30)
    btn_prev = Button(ax_prev, '◄ 100ms')

    # Slider: 0.25'ten başla (butonla arasında 5% boşluk) ve genişliği 0.5 yap
    ax_slider = fig.add_axes([0.25, widget_bottom, 0.50, widget_height]);
    ax_slider.set_in_layout(False);
    ax_slider.set_zorder(30)
    slider = Slider(ax=ax_slider, label='Time (ms)', valmin=0.0, valmax=t_max, valinit=float(t_init_ms), valstep=10.0)

    # Sağ buton: 0.80'den başla (slider ile arasında 5% boşluk)
    ax_next = fig.add_axes([0.80, widget_bottom, 0.10, widget_height]);
    ax_next.set_in_layout(False);
    ax_next.set_zorder(30)
    btn_next = Button(ax_next, '100ms ►')

    # --- toolbar kilidini otomatik kapat (zoom/pan) ---
    def _disarm_toolbar():
        mgr = getattr(fig.canvas, "manager", None)
        tb = getattr(mgr, "toolbar", None)
        try:
            if tb is not None and getattr(tb, "mode", ""):
                try:
                    tb.pan()
                except:
                    pass
                try:
                    tb.zoom()
                except:
                    pass
                try:
                    fig.canvas.widgetlock.release(tb)
                except:
                    pass
                try:
                    tb._active = None
                except:
                    pass
        except:
            pass

    def _on_axes_enter(ev):
        if ev.inaxes in (ax_slider, ax_prev, ax_next):
            _disarm_toolbar()

    fig.canvas.mpl_connect('axes_enter_event', _on_axes_enter)

    # --- update ---
    def _update(val):
        t_ms = float(slider.val)
        prof_AA = _build_profile(syn_AA, wmon_AA, t_ms, n_mem)
        prof_AB = _build_profile(syn_AB, wmon_AB, t_ms, n_mem)
        prof_BB = _build_profile(syn_BB, wmon_BB, t_ms, n_mem)
        prof_BA = _build_profile(syn_BA, wmon_BA, t_ms, n_mem)

        if prof_AA is not None: line_AA.set_data(x_idx[:len(prof_AA)], prof_AA)
        if prof_AB is not None: line_AB.set_data(x_idx[:len(prof_AB)], prof_AB)
        if prof_BB is not None: line_BB.set_data(x_idx[:len(prof_BB)], prof_BB)
        if prof_BA is not None: line_BA.set_data(x_idx[:len(prof_BA)], prof_BA)

        fig.suptitle(f"Mean outgoing synaptic weights by memory neuron (t ≈ {t_ms:.0f} ms)")
        fig.canvas.draw_idle()

    slider.on_changed(_update)

    def _next(event):
        _disarm_toolbar()
        slider.set_val(min(slider.val + 500.0, slider.valmax))

    def _prev(event):
        _disarm_toolbar()
        slider.set_val(max(slider.val - 500.0, slider.valmin))

    btn_next.on_clicked(_next)
    btn_prev.on_clicked(_prev)

    _disarm_toolbar()
    _update(t_init_ms)
    return fig, slider, btn_prev, btn_next











def analyze_omission_response(mon_pe_A, tones, times, paradigm_params, window_start_ms=0, window_end_ms=250):
    """
    Belirli bir zaman ARALIĞINDAKİ PE nöronu ateşlemelerini sayarak Omission
    etkisini sayısal olarak ölçen GÜNCELLENMİŞ fonksiyon.
    """
    print("\n" + "-" * 50)
    print("--- OMISSION ETKİSİ SAYISAL ANALİZİ ---")

    isi = paradigm_params['isi']
    start_window = window_start_ms * ms
    end_window = window_end_ms * ms

    t_standard_response_event = None
    t_omission_response_event = None

    for i in range(len(times) - 1):
        if abs((times[i + 1] - times[i]) - isi) < 0.01 * ms:
            t_standard_response_event = times[i + 1]
            break

    for i in range(len(times) - 1):
        if abs((times[i + 1] - times[i]) - (2 * isi)) < 0.01 * ms:
            t_omission_response_event = times[i] + isi
            break

    if t_standard_response_event is None or t_omission_response_event is None:
        print("UYARI: Analiz için uygun standart ('AA') veya omission ('A_') olayı bulunamadı.")
        print("-" * 50 + "\n")
        return

    # Spike sayımlarını yeni aralığa göre yap
    std_mask = (mon_pe_A.t >= t_standard_response_event + start_window) & (
            mon_pe_A.t < t_standard_response_event + end_window)
    std_spike_count = len(mon_pe_A.t[std_mask])

    dev_mask = (mon_pe_A.t >= t_omission_response_event + start_window) & (
            mon_pe_A.t < t_omission_response_event + end_window)
    dev_spike_count = len(mon_pe_A.t[dev_mask])

    # Raporlama metnini yeni aralığa göre güncelle
    print(f"Analiz Penceresi: Olay sonrası {window_start_ms} ms ile {window_end_ms} ms arası")
    print(f"Standart Tepki ('AA'deki 2. A'ya): {std_spike_count} PE_A spikes")
    print(f"Omission Tepkisi ('A_' boşluğuna): {dev_spike_count} PE_A spikes")

    if dev_spike_count > std_spike_count:
        print(">>> SONUÇ: Omission etkisi gözlemlendi (Beklenen ama gelmeyen sese verilen hata tepkisi daha yüksek).")
    else:
        print(">>> SONUÇ: Beklenen omission etkisi gözlemlenmedi.")
    print("-" * 50 + "\n")


def plot_omission_response_comparison(monitors_A, thalamic_spikemon, thalamic_statemon,
                                      memory_module_A, tones, times,
                                      paradigm_params, N_input_per_tone,
                                      window_start_ms=-50, window_end_ms=250):
    """
    Omission paradigması için, 4 katmanın da aktivitesini gösteren,
    makale formatında bir karşılaştırma grafiği çizen GÜNCELLENMİŞ fonksiyon.
    """
    print(">>> Omission Karşılaştırma Grafiği (Tüm Katmanlar) oluşturuluyor...")

    isi = paradigm_params['isi']
    # Zaman aralığını artık hardcoded değil, parametrelerden al
    time_window = np.array([window_start_ms, window_end_ms]) * ms

    t_standard_response_event = None
    t_omission_response_event = None

    for i in range(len(times) - 1):
        if abs((times[i + 1] - times[i]) - isi) < 0.01 * ms:
            t_standard_response_event = times[i + 1]
            break

    for i in range(len(times) - 1):
        if abs((times[i + 1] - times[i]) - (2 * isi)) < 0.01 * ms:
            t_omission_response_event = times[i] + isi
            break

    if t_standard_response_event is None or t_omission_response_event is None:
        print("UYARI: Omission grafiği için uygun standart ('AA') veya omission ('A_') olayı bulunamadı.")
        return

    def get_windowed_data(monitor, t_event):
        if monitor is None: return (None, None)
        t_start, t_end = t_event + time_window[0], t_event + time_window[1]
        if isinstance(monitor, SpikeMonitor):
            mask = (monitor.t >= t_start) & (monitor.t < t_end)
            return (monitor.t[mask] - t_event) / ms, monitor.i[mask]
        elif isinstance(monitor, StateMonitor):
            mask = (monitor.t >= t_start) & (monitor.t < t_end)
            if not np.any(mask): return np.array([]), np.array([])
            valid_slice = monitor.v[:, mask]
            if valid_slice.shape[1] == 0: return np.array([]), np.array([])
            return (monitor.t[mask] - t_event) / ms, np.mean(valid_slice / mV, axis=0)
        elif isinstance(monitor, tuple):
            t_all, i_all = monitor;
            mask = (t_all >= t_start) & (t_all < t_end)
            return (t_all[mask] - t_event) / ms, i_all[mask]
        return (None, None)

    data = {'standard': {}, 'omission': {}}
    thalamic_A_spikes = (thalamic_spikemon.t[thalamic_spikemon.i < N_input_per_tone],
                         thalamic_spikemon.i[thalamic_spikemon.i < N_input_per_tone])

    all_mons = {**monitors_A, **memory_module_A,
                'thalamic_statemon': thalamic_statemon,
                'thalamic_spikemon': thalamic_A_spikes}

    layers = [
        {'title': 'Memory trace', 'spikes': 'spikemon_mem_e', 'vm': 'statemon_mem_e'},
        {'title': 'Predictive Layer', 'spikes': 'spikemon_p', 'vm': 'statemon_p'},
        {'title': 'Prediction Error Layer', 'spikes': 'spikemon_pe', 'vm': 'statemon_pe'},
        {'title': 'Thalamic Input', 'spikes': 'thalamic_spikemon', 'vm': 'thalamic_statemon'}
    ]

    for condition, event_time in [('standard', t_standard_response_event), ('omission', t_omission_response_event)]:
        for layer in layers:
            data[condition][layer['spikes']] = get_windowed_data(all_mons.get(layer['spikes']), event_time)
            data[condition][layer['vm']] = get_windowed_data(all_mons.get(layer['vm']), event_time)

    fig = plt.figure(figsize=(14, 14))
    fig.suptitle("Standart ('AA') ve Omission ('A_') Tepkilerinin Karşılaştırılması", fontsize=16)

    main_grid = fig.add_gridspec(4, 2, hspace=0.7, wspace=0.25, left=0.15, right=0.95)
    ref_ax = None

    for col_idx, condition in enumerate(['standard', 'omission']):
        for row_idx, layer_info in enumerate(layers):

            inner_grid = main_grid[row_idx, col_idx].subgridspec(2, 1, hspace=0.1, height_ratios=[2, 1.5])
            ax_raster = fig.add_subplot(inner_grid[0, 0])
            ax_vm = fig.add_subplot(inner_grid[1, 0], sharex=ax_raster)

            t_vm, v_mean = data[condition][layer_info['vm']]
            if t_vm is not None and len(t_vm) > 0:
                ax_vm.plot(t_vm, v_mean, 'k')
            ax_vm.set_ylim(-80, 45)

            t_spk, i_spk = data[condition][layer_info['spikes']]
            if t_spk is not None and len(t_spk) > 0:
                ax_raster.plot(t_spk, i_spk, '.k', ms=2)

            if ref_ax is None:
                ref_ax = ax_raster
            else:
                ax_raster.sharex(ref_ax)

            plt.setp(ax_raster.get_xticklabels(), visible=False)

            if col_idx == 0:
                ax_raster.set_ylabel(f"{layer_info['title']}\n\nNöron Indeksi")
                ax_vm.set_ylabel('Ort. Vm\n(mV)')

            if row_idx == 0:
                ax_raster.set_title(
                    "Standart Tepki (2. A'dan Sonra)" if condition == 'standard' else "Omission Tepkisi (Boşlukta)",
                    pad=15)

            if row_idx == len(layers) - 1:
                ax_vm.set_xlabel("Olay Zamanından İtibaren Zaman (ms)")
            else:
                plt.setp(ax_vm.get_xticklabels(), visible=False)

    if ref_ax:
        ref_ax.set_xlim(time_window / ms)


# ======================================================================
# BÖLÜM 2: AĞ MİMARİSİ "FABRİKA" FONKSİYONLARI
# ======================================================================

def create_neuron_group(n_neurons, name, neuron_type, params):
    # --- FPGA DOSTU LIF MODELİ (DÜZELTİLMİŞ) ---

    # Çekirdek denklem: Tüm nöronlar I_syn toplamını bekler
    core_eqs = '''
    dv/dt = (-(v - v_rest) + I_syn) / tau_m : volt (unless refractory)
    I_syn = I_ampa + I_gaba + I_nmda : volt

    v_rest : volt
    v_threshold : volt
    v_reset : volt
    tau_m : second
    '''

    # --- INPUT NÖRONLARI ---
    if neuron_type == 'input':
        # Input nöronları sadece stimulus akımı alır, I_syn kullanmaz (0 yapılır)
        full_eqs = '''
        dv/dt = (-(v - v_rest) + stimulus_current(t, i)) / tau_m : volt (unless refractory)
        v_rest : volt
        v_threshold : volt
        v_reset : volt
        tau_m : second
        I_syn = 0*mV : volt
        '''

    # --- EXCITATORY (UYARICI) NÖRONLAR ---
    elif neuron_type == 'excitatory':
        syn_eq = '''
        # AMPA (Hızlı Uyarıcı)
        I_ampa = g_ampa*(V_E - v)*s_ampa : volt
        ds_ampa/dt = -s_ampa/tau_ampa : 1

        # GABA (Baskılayıcı)
        I_gaba = g_gaba*(V_I - v)*s_gaba : volt
        ds_gaba/dt = -s_gaba/tau_gaba : 1

        # NMDA (Yavaş Uyarıcı - Öğrenme İçin)
        I_nmda = g_nmda*(V_E - v)*s_nmda / (1 + Mg2_conc * exp(-0.062*v/mV) / 3.57) : volt
        ds_nmda/dt = -s_nmda/tau_nmda_decay + alpha_nmda*x_nmda*(1-s_nmda) : 1
        dx_nmda/dt = -x_nmda/tau_nmda_rise : 1

        V_E:volt
        V_I:volt
        g_ampa:1
        g_gaba:1
        g_nmda:1
        Mg2_conc:1
        tau_ampa:second
        tau_gaba:second
        tau_nmda_rise:second
        tau_nmda_decay:second
        alpha_nmda:Hz
        '''
        full_eqs = core_eqs + syn_eq

    # --- INHIBITORY (BASKILAYICI) NÖRONLAR ---
    elif neuron_type == 'inhibitory':
        syn_eq = '''
        # AMPA
        I_ampa = g_ampa*(V_E - v)*s_ampa : volt
        ds_ampa/dt = -s_ampa/tau_ampa : 1

        # GABA (EKLENDİ: Inhibitörler de birbirini baskılayabilir veya dışardan alabilir)
        I_gaba = g_gaba*(V_I - v)*s_gaba : volt
        ds_gaba/dt = -s_gaba/tau_gaba : 1

        # NMDA
        I_nmda = g_nmda*(V_E - v)*s_nmda / (1 + Mg2_conc * exp(-0.062*v/mV) / 3.57) : volt
        ds_nmda/dt = -s_nmda/tau_nmda_decay + alpha_nmda*x_nmda*(1-s_nmda) : 1
        dx_nmda/dt = -x_nmda/tau_nmda_rise : 1

        V_E:volt
        V_I:volt # EKLENDİ: GABA için gerekli
        g_ampa:1
        g_gaba:1 # EKLENDİ
        g_nmda:1
        Mg2_conc:1
        tau_ampa:second
        tau_gaba:second # EKLENDİ
        tau_nmda_rise:second
        tau_nmda_decay:second
        alpha_nmda:Hz
        '''
        full_eqs = core_eqs + syn_eq

    # Eşik değeri parametreden dinamik alıyoruz
    # DÜZELTME: refractory='2*ms' eklendi.
    group = NeuronGroup(n_neurons, full_eqs,
                        threshold='v > v_threshold',
                        reset='v = v_reset',
                        refractory='2*ms',
                        method='euler',
                        name=name)

    # Parametreleri ayarla
    for key, value in params.items():
        if hasattr(group, key):
            setattr(group, key, value)

    # Başlangıç değerleri
    if hasattr(group, 'v_rest'):
        group.v = group.v_rest

    return group


def create_synaptic_connection(source, target, conn_prob, w_model, on_pre_action, delay_model=None, cond=None,
                               name=None):
    """
    İki nöron grubu arasında statik bir sinaptik bağlantı oluşturur.
    Artık dışarıdan bir 'name' parametresi alabilir.
    """
    # Eğer dışarıdan bir isim verilmediyse, eskisi gibi otomatik bir isim oluştur.
    # Eğer verildiyse, o ismi kullan.
    syn_name = name if name is not None else f'syn_{source.name}_{target.name}'

    syn = Synapses(source, target, model='w:1', on_pre=on_pre_action, name=syn_name)

    if cond:
        syn.connect(condition=cond)
    else:
        syn.connect(p=conn_prob)

    syn.w = w_model
    if delay_model:
        syn.delay = delay_model

    return syn


# MMN.py dosyanızdaki mevcut create_plastic_synapse fonksiyonunu
# aşağıdaki kod bloğu ile tamamen değiştirin.

def create_plastic_synapse(source, target, conn_prob, initial_w, delay_model=None, conn_data=None, plasticity_on=True):
    """
    Memory -> Predictive için NMDA-kapılı STDP (Wacongne+).
    """
    print(f"'{source.name}' -> '{target.name}' arasında PLASTİK sinaps (Kural: NMDA-kapılı STDP, Plastisite: {'AÇIK' if plasticity_on else 'KAPALI'}).")

    taup_val = 30*ms   # τp
    cp_val   = 60.0    # cp
    cd_val   = 5.0   # cd
    Th_val   = 0.6     # eşik
    eta_val  = 5e-6    # öğrenme ölçeği (gerekirse ayarlanabilir)
    I_to_u   = 1.0     # INMDA ölçekleme

    if plasticity_on:
        stdp_model = '''
        w : 1
        dApre/dt  = -Apre/taup : 1 (event-driven)
        dApost/dt = -Apost/taup : 1 (event-driven)
        taup : second (constant)
        cp   : 1 (constant)
        cd   : 1 (constant)
        Th   : 1 (constant)
        eta  : 1 (constant)
        Iu   : 1 (constant)
        wmin : 1 (constant)
        wmax : 1 (constant)
        '''
        on_pre_action = '''
        s_ampa_post += w
        x_nmda_post += w * 0.25
        Apre += 1
        w = w + eta*( cp*clip((I_nmda_post/mV - Th), 0, 1e9)*Apost*x_gate_pre - cd*x_gate_pre )
        w = clip(w, wmin, wmax)
        '''
        on_post_action = '''
        Apost += 1
        w = w + eta*( cp*clip((I_nmda_post/mV - Th), 0, 1e9)*Apre*x_gate_pre )
        w = clip(w, wmin, wmax)
        '''
    else:
        stdp_model = 'w : 1'
        on_pre_action = 's_ampa_post += w; x_nmda_post += w * 0.2'
        on_post_action = ''

    syn = Synapses(source, target, model=stdp_model,
                   on_pre=on_pre_action, on_post=on_post_action,
                   name=f'nmda_stdp_syn_{source.name}_{target.name}')

    if conn_data is not None:
        syn.connect(i=conn_data['i'], j=conn_data['j'])
    else:
        syn.connect(p=conn_prob)

    syn.w    = initial_w
    syn.taup = taup_val
    syn.cp   = cp_val
    syn.cd   = cd_val
    syn.Th   = Th_val
    syn.eta  = eta_val
    syn.Iu   = I_to_u
    syn.wmin = 0.0
    syn.wmax = 10.0

    if delay_model:
        syn.delay = delay_model

    return syn


def create_hebbian_synapse(pre_grp, post_grp, w_init, *,
                           conn_data=None,
                           delay_model='rand()*15*ms',
                           step=0.1,           # sabit artis miktari (dW)
                           w_min=0.0, w_max=10.0,
                           name=None):
    if name is None:
        # Sadece ASCII kullan
        name = f"hebb_{pre_grp.name}_to_{post_grp.name}"

    syn = Synapses(
        pre_grp, post_grp,
        model='''
        w     : 1
        w_min : 1
        w_max : 1
        step  : 1
        ''',
        on_pre='''
        s_ampa_post = s_ampa_post + w
        x_nmda_post = x_nmda_post + w*0.2
        w = clip(w + step, w_min, w_max)
        ''',
        name=name
    )
    if conn_data is not None:
        syn.connect(i=conn_data['i'], j=conn_data['j'])
    else:
        syn.connect(p=0.5)
    syn.w = w_init
    syn.w_min = w_min
    syn.w_max = w_max
    syn.step = step
    syn.delay = delay_model
    return syn


def create_stdp_synapse(pre_grp, post_grp, w_init, *,
                        conn_data=None,
                        delay_model='rand()*15*ms',
                        w_min=0.0, w_max=4.0,
                        A_plus=0.02,        # LTP gücü (değişmeden kalsın)
                        A_minus=-0.03,      # LTD izi (post spike'ta Apost += A_minus)
                        taupre_ms=15.0,
                        taupost_ms=25.0,
                        multiplicative=True,   # ağırlık-bağımlı STDP
                        ltd_gain=2.0,          # <<< YENİ: LTD etkisini çarpan
                        name=None):
    from brian2 import Synapses, ms

    if name is None:
        name = f"stdp_{pre_grp.name}_to_{post_grp.name}"

    model = '''
    w      : 1
    w_min  : 1
    w_max  : 1
    A_plus : 1
    A_minus: 1
    taupre  : second
    taupost : second
    dApre/dt  = -Apre/taupre  : 1 (event-driven)
    dApost/dt = -Apost/taupost: 1 (event-driven)
    '''

    if multiplicative:
        # LTP değişmedi; LTD tarafında sadece Apost etkisini ltd_gain ile çarpıyoruz.
        on_pre = '''
        s_ampa_post += w
        x_nmda_post += w*0.2
        w = clip(w + (''' + str(float(ltd_gain)) + ''')*Apost*(w - w_min), w_min, w_max)
        Apre += A_plus
        '''
        on_post = '''
        w = clip(w + Apre*(w_max - w), w_min, w_max)
        Apost += A_minus
        '''
    else:
        on_pre = '''
        s_ampa_post += w
        x_nmda_post += w*0.2
        w = clip(w + (''' + str(float(ltd_gain)) + ''')*Apost, w_min, w_max)
        Apre += A_plus
        '''
        on_post = '''
        w = clip(w + Apre, w_min, w_max)
        Apost += A_minus
        '''

    syn = Synapses(pre_grp, post_grp, model=model,
                   on_pre=on_pre, on_post=on_post, name=name)

    if conn_data is not None:
        syn.connect(i=conn_data['i'], j=conn_data['j'])
    else:
        syn.connect(p=0.5)

    syn.w = w_init
    syn.w_min = w_min
    syn.w_max = w_max
    syn.A_plus = A_plus
    syn.A_minus = A_minus
    syn.taupre = taupre_ms * ms
    syn.taupost = taupost_ms * ms
    syn.Apre = 0
    syn.Apost = 0
    syn.delay = delay_model
    return syn






def create_cortical_column(column_id, N_exc, N_inh, params_exc, params_inh, synaptic_weights, record_states=True):
    """
    Kortikal Kolon oluşturur. record_states=False ise performans için StateMonitor'lar (voltaj kaydı) oluşturulmaz.
    """
    print(f"Kortikal Kolon '{column_id}' oluşturuluyor... (Detaylı Monitörler: {record_states})")
    PE = create_neuron_group(N_exc, f'PE_{column_id}', 'excitatory', params_exc)
    P = create_neuron_group(N_exc, f'P_{column_id}', 'excitatory', params_exc)
    I = create_neuron_group(N_inh, f'I_{column_id}', 'inhibitory', params_inh)
    w = synaptic_weights;
    delay = 'rand()*15*ms'
    on_pre_exc = 's_ampa_post = s_ampa_post + w; x_nmda_post = x_nmda_post + w * 0.2'
    on_pre_inh = 's_gaba_post = s_gaba_post + w'
    syn_P_I = create_synaptic_connection(P, I, 0.95, w["w_EI"], on_pre_exc, delay_model=delay,
                                         name=f'syn_P_I_{column_id}')
    syn_I_PE = create_synaptic_connection(I, PE, 0.95, w["w_IE"], on_pre_inh, delay_model=delay,
                                          name=f'syn_I_PE_{column_id}')
    syn_PE_P = create_synaptic_connection(PE, P, 0.95, w["w_EE"], on_pre_exc, delay_model=delay,
                                          name=f'syn_PE_P_{column_id}')

    monitors = {
        'spikemon_pe': SpikeMonitor(PE, name=f'spikemon_pe_{column_id}'),
        'ratemon_pe': PopulationRateMonitor(PE, name=f'ratemon_pe_{column_id}'),
        'spikemon_p': SpikeMonitor(P, name=f'spikemon_p_{column_id}'),
        'ratemon_p': PopulationRateMonitor(P, name=f'ratemon_p_{column_id}'),
        'spikemon_i': SpikeMonitor(I, name=f'spikemon_i_{column_id}'),
        'ratemon_i': PopulationRateMonitor(I, name=f'ratemon_i_{column_id}')
    }

    if record_states:
        neurons_to_record = range(min(10, N_exc))
        monitors['statemon_pe'] = StateMonitor(PE, ['v', 'I_syn'], record=neurons_to_record, dt=1 * ms,
                                               name=f'statemon_pe_{column_id}')
        monitors['statemon_p'] = StateMonitor(P, ['v', 'I_syn'], record=neurons_to_record, dt=1 * ms,
                                              name=f'statemon_p_{column_id}')
        monitors['statemon_i'] = StateMonitor(I, ['v', 'I_syn'], record=range(min(10, N_inh)), dt=1 * ms,
                                              name=f'statemon_i_{column_id}')

    return {'PE': PE, 'P': P, 'I': I, 'syn_P_I': syn_P_I, 'syn_I_PE': syn_I_PE, 'syn_PE_P': syn_PE_P, **monitors}


def create_memory_module(module_id, params_mem, N_E_mem, N_I_mem):
    print(f"Özelleştirilmiş 'Bellek Modülü {module_id}' oluşturuluyor...")
    params_exc_mem = params_mem['exc']
    params_inh_mem = params_mem['inh']
    w = params_mem['weights']

    E_chain = create_neuron_group(N_E_mem, f'E_chain_Mem_{module_id}', 'excitatory', params_exc_mem)
    I_pool = create_neuron_group(N_I_mem, f'I_pool_Mem_{module_id}', 'inhibitory', params_inh_mem)

    on_pre_e = 's_ampa_post = s_ampa_post + w; x_nmda_post = x_nmda_post + w*0.2'
    on_pre_i = 's_gaba_post = s_gaba_post + w'

    syn_ee_mem = create_synaptic_connection(E_chain, E_chain, None, f'{w["w_EE_mem"]}*(1+0.05*randn())', on_pre_e,
                                            delay_model=w["CHAIN_DELAY"], cond='i==j-1')
    syn_ei_mem = create_synaptic_connection(E_chain, I_pool, w["p_EI"], f'{w["w_EI_mem"]}*(1+0.05*randn())', on_pre_e,
                                            delay_model=w["E_TO_I_DELAY"])
    syn_ie_mem = create_synaptic_connection(I_pool, E_chain, w["p_IE"], f'{w["w_IE_mem"]}*(1+0.05*randn())', on_pre_i,
                                            delay_model=w["I_TO_E_DELAY"])

    spikemon_mem_e = SpikeMonitor(E_chain, name=f's_mem_e_{module_id}')

    return {'E_chain': E_chain, 'I_pool': I_pool, 'syn_ee': syn_ee_mem, 'syn_ei': syn_ei_mem,
            'syn_ie': syn_ie_mem, 'spikemon_mem_e': spikemon_mem_e}


def create_simple_memory_module(module_id, simple_params, N_chain):
    # Parametrelerden süreleri çekelim
    # Önemli: t_ref_head (baş nöronun beklemesi) > Stimulus Süresi (50ms) olmalı!
    t_ref_head = 200 * ms
    t_ref_tail = 2 * ms

    v_rest = simple_params.get('v_rest', 0.0)
    tau_m = simple_params.get('tau_m', 20 * ms)
    J_ff = float(simple_params.get('J_ff', 1.1))
    d_ff = simple_params.get('d_ff', 6 * ms)

    # DÜZELTME: 'ref_time' değişkenini doğrudan denklemlerin içine ekledik.
    eqs = f'''
    dv/dt = (-(v - {v_rest}))/tau_m : 1 (unless refractory)
    ref_time : second
    tau_m : second
    '''

    # Nöron grubunu oluştur
    E_chain = NeuronGroup(N_chain, model=eqs,
                          threshold='v > 1.0',
                          reset='v = 0',
                          refractory='ref_time',  # Brian2 artık 'ref_time'ı eqs içinden okuyacak
                          method='euler',
                          name=f'E_chain_{module_id}')

    # Parametreleri ata
    E_chain.tau_m = tau_m

    # --- Refractory sürelerini ayarla ---
    # Önce hepsine kısa süreyi ata (State variable olduğu için dizi olarak başlatılır)
    E_chain.ref_time = t_ref_tail

    # Sonra sadece ilk nörona (kapı nöronu) uzun süreyi ata
    E_chain.ref_time[0] = t_ref_head

    # Zincir içi bağlantı (Domino etkisi)
    syn_ee_mem = Synapses(E_chain, E_chain, model='w:1',
                          on_pre=f'v_post = v_post + w*{J_ff}',
                          name=f'syn_chain_{module_id}')
    syn_ee_mem.connect(condition='i==j-1')
    syn_ee_mem.delay = d_ff
    syn_ee_mem.w = 1.0

    spikemon_mem_e = SpikeMonitor(E_chain, name=f's_mem_e_{module_id}')

    # I_pool vb. kullanmıyoruz artık, None dönüyoruz
    return {'E_chain': E_chain, 'I_pool': None, 'syn_ee': syn_ee_mem,
            'syn_ei': None, 'syn_ie': None, 'spikemon_mem_e': spikemon_mem_e}


def _ensure_no_consecutive_deviants(tones_array):
    """
    Aykırı seslerin (1'ler) asla yan yana gelmeyeceği bir dizi oluşturur.
    Bu yöntem, rastgele karıştırma yerine diziyi doğrudan inşa ettiği için
    hızlı ve garantilidir.
    """
    # 1. Dizideki standart (0) ve aykırı (1) seslerin sayısını bul.
    n_standards = np.count_nonzero(tones_array == 0)
    n_deviants = np.count_nonzero(tones_array == 1)

    # Eğer aykırı sesleri standart seslerin arasına ve kenarlarına yerleştirmek
    # matematiksel olarak imkansızsa (çok fazla aykırı ses varsa) uyar.
    if n_deviants > n_standards + 1:
        raise ValueError(f"{n_deviants} aykırı ses, {n_standards} standart sesin arasına "
                         f"yan yana gelmeyecek şekilde yerleştirilemez.")

    # 2. Önce sadece standart seslerden oluşan bir 'temel' oluştur.
    # Örn: [0, 0, 0, 0, 0]
    result = np.zeros(n_standards, dtype=int)

    # 3. Aykırı sesleri yerleştirebileceğimiz potansiyel 'boşlukları' bul.
    # Beş tane sıfır için 6 potansiyel boşluk vardır: _ 0 _ 0 _ 0 _ 0 _ 0 _
    possible_indices = np.arange(n_standards + 1)

    # 4. Bu potansiyel boşluklardan, aykırı ses sayısı kadarını rastgele seç.
    # Örn: 6 boşluktan 3 tanesini seç (diyelim ki 0, 3, 5. pozisyonlar)
    chosen_indices = np.random.choice(possible_indices, n_deviants, replace=False)

    # 5. Aykırı sesleri (1'leri) bu seçilen pozisyonlara tek tek ekle.
    # np.insert fonksiyonu, diziyi kaydırarak ekleme yapar.
    # Her eklemeden sonra indisler kayacağı için, büyükten küçüğe doğru ekleme yaparız.
    chosen_indices.sort()
    for index in chosen_indices[::-1]:
        result = np.insert(result, index, 1)

    return result


def create_paradigm_sequence(paradigm_name, params):
    print(f"'{paradigm_name}' paradigması için dizi oluşturuluyor...")
    tones, times = None, None

    if paradigm_name == 'classic':
        total_tones = params['total_tones']
        deviant_prob = params['deviant_prob']
        soa = params['soa']  # ms gibi Brian2 birimi
        min_dev_ms = params.get('min_deviant_ms', 0 * ms)

        n_deviants = int(total_tones * deviant_prob)
        n_standards = total_tones - n_deviants

        # İlk deviant’ın başlayabileceği minimum indis (10 sn / SOA)
        min_dev_idx = int(np.ceil((min_dev_ms / soa))) if min_dev_ms > 0 * ms else 0
        if min_dev_idx < 0:
            min_dev_idx = 0
        if min_dev_idx > total_tones:
            min_dev_idx = total_tones  # tüm dizi “standart” olur

        # Fezibilite kontrolü: İlk min_dev_idx tamamen standart olacak.
        rem_slots = total_tones - min_dev_idx
        rem_standards = n_standards - min_dev_idx
        if rem_standards < 0:
            raise ValueError(
                f"min_deviant_ms çok büyük: İlk {min_dev_idx} tonu standart ayırmak istiyorsun "
                f"ama toplam standart sayın {n_standards}. "
                f"total_tones / deviant_prob / soa değerlerini yeniden gözden geçir."
            )
        # Yan yana deviant istemiyorsak gerekli koşul: n_deviants <= rem_standards + 1
        if n_deviants > rem_standards + 1:
            raise ValueError(
                "İlk {min_dev_idx} ton tamamen standart kalınca kalan aralıkta "
                "deviant’ları yan yana gelmeyecek biçimde yerleştirmek mümkün değil. "
                "deviant_prob’u küçült ya da min_deviant_ms’yi düşür."
            )

        # ÖN EK: (ilk 10 sn) tamamı 0 (standart)
        prefix = np.zeros(min_dev_idx, dtype=int)

        # KALAN KISIM: (min_dev_idx ... son) – burada deviant’ları yerleştir
        segment_base = np.array([0] * rem_standards + [1] * n_deviants)
        segment_tones = _ensure_no_consecutive_deviants(segment_base)

        # Birleştir
        tones = np.concatenate([prefix, segment_tones])
        times = np.arange(total_tones) * soa



    elif paradigm_name == 'alternating':

        print(" -> 'alternating' paradigması için dizi oluşturuluyor (10 sn öncesi deviant yok).")

        total_tones = params['total_tones']

        deviant_prob = params['deviant_prob']

        soa = params['soa']

        min_dev_ms = params.get('min_deviant_ms', 0 * ms)  # <<< YENİ

        # 1) Temel ABAB... dizisini kur

        tones = np.tile([0, 1], total_tones // 2)

        if total_tones % 2 != 0:
            tones = np.append(tones, 0)

        # 2) Sadece min_dev_ms SONRASINDA deviant uygula (B->A çevirme)

        if 0 < deviant_prob < 1.0:

            b_indices = np.where(tones == 1)[0]  # mevcut kodla aynı başlangıç noktası

            # min_dev_ms'ye karşı düşen minimum indis

            min_dev_idx = int(np.ceil((min_dev_ms / soa))) if min_dev_ms > 0 * ms else 0

            # Yalnızca bu indisten SONRAKİ B'ler deviant adayı

            allowed = b_indices[b_indices >= min_dev_idx]

            # Not: Aşağıda oranı "kalan B'ler" üzerinden alıyoruz.

            # Toplam oranı muhafaza etmek istersen len(b_indices) ile ölçekleyebilirsin.

            num_to_change = int(len(allowed) * deviant_prob)

            if num_to_change > 0 and len(allowed) > 0:
                indices_to_change = np.random.choice(allowed, size=num_to_change, replace=False)

                tones[indices_to_change] = 0  # B->A (deviant)

        times = np.arange(len(tones)) * soa


    elif paradigm_name == 'local_global':
        num_sequences = params['num_sequences'];
        intra_isi = params['intra_isi'];
        inter_soa = params['inter_soa']
        probabilities = params['probabilities']
        sequence_map = {'standard': 'AAAAB', 'deviant': 'AAAAA', 'omission': 'AAAA'}
        chosen_sequences = np.random.choice(list(sequence_map.keys()), num_sequences, p=probabilities)
        full_tone_string = "".join([sequence_map[s] for s in chosen_sequences])
        tones = np.array([0 if T == 'A' else 1 for T in full_tone_string])
        time_list = []
        current_time = 0 * ms
        for seq_type in chosen_sequences:
            seq_length = len(sequence_map[seq_type])
            times_in_seq = current_time + np.arange(seq_length) * intra_isi
            time_list.extend(times_in_seq)
            current_time += (seq_length - 1) * intra_isi + inter_soa
        times = Quantity(time_list)

    elif paradigm_name == 'omission':
        num_pairs = params['num_pairs'];
        omission_prob = params['omission_prob'];
        isi = params['isi']
        num_omissions = int(num_pairs * omission_prob);
        num_doubles = num_pairs - num_omissions
        blocks = ['AA'] * num_doubles + ['A'] * num_omissions
        np.random.shuffle(blocks)
        tone_list, time_list = [], []
        current_time = 0 * ms
        for block in blocks:
            if block == 'AA':
                tone_list.extend([0]);
                time_list.extend([current_time])
            else:
                tone_list.extend([1]);
                time_list.extend([current_time])
            current_time += 2 * isi
        tones = np.array(tone_list)
        times = Quantity(time_list)

    else:
        raise ValueError(f"Bilinmeyen paradigma: {paradigm_name}")

    return tones, times


def plot_thalamic_input_only(spike_mon, total_duration, N_input_per_tone, start_ms=None, end_ms=None):
    """
    Sadece Talamik Girdi aktivitesini gösteren bir raster grafiği çizer.
    Girdi A ve Girdi B'yi ayrı alt grafiklerde gösterir ve istenen zaman
    aralığına odaklanma imkanı sunar.
    """
    print(
        f">>> Talamik Girdi Test Grafiği oluşturuluyor (Zaman Aralığı: {start_ms if start_ms is not None else 0}ms - {end_ms if end_ms is not None else total_duration / ms:.0f}ms)...")

    # A ve B tonlarına ait spikeları ayır
    mask_A = spike_mon.i < N_input_per_tone
    t_A, i_A = spike_mon.t[mask_A], spike_mon.i[mask_A]

    mask_B = spike_mon.i >= N_input_per_tone
    t_B, i_B = spike_mon.t[mask_B], spike_mon.i[mask_B] - N_input_per_tone  # Nöron indekslerini 0'dan başlatmak için

    # 2 satırlı bir grafik alanı oluştur (x eksenini paylaşacaklar)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 10), sharex=True)
    fig.suptitle('Talamik Girdi Aktivitesi Testi', fontsize=16)

    # Üstteki grafik: Girdi A
    ax1.set_title('Girdi A (Standart Tonlar)')
    ax1.plot(t_A / ms, i_A, '.b', ms=3)
    ax1.set_ylabel('Nöron İndeksi')
    ax1.grid(True, linestyle='--', alpha=0.5)

    # Alttaki grafik: Girdi B
    ax2.set_title('Girdi B (Aykırı Tonlar)')
    ax2.plot(t_B / ms, i_B, '.r', ms=3)
    ax2.set_ylabel('Nöron İndeksi')
    ax2.set_xlabel('Zaman (ms)')
    ax2.grid(True, linestyle='--', alpha=0.5)

    # Zaman aralığı kontrolü
    # Eğer bir bitiş zamanı verilmediyse, tüm simülasyon süresini kullan
    plot_start_ms = start_ms if start_ms is not None else 0
    plot_end_ms = end_ms if end_ms is not None else total_duration / ms

    # Eksen limitlerini ayarla
    plt.xlim(plot_start_ms, plot_end_ms)

    plt.tight_layout(rect=[0, 0, 1, 0.96])


def plot_debug_window(monitors, title, start_ms, end_ms):
    """
    Belirtilen monitörlerin aktivitesini, belirtilen dar bir zaman aralığında çizer.
    Hata ayıklama için kullanılır.
    """
    print(f">>> Hata Ayıklama Penceresi Çiziliyor: '{title}' ({start_ms}ms - {end_ms}ms)")

    spike_mon = monitors.get('spikemon')
    state_mon = monitors.get('statemon')

    fig, axes = plt.subplots(2, 1, figsize=(20, 10), sharex=True)
    fig.suptitle(f'Hata Ayıklama: {title}', fontsize=16)

    # Raster Plot
    if spike_mon and len(spike_mon.t) > 0:
        axes[0].plot(spike_mon.t / ms, spike_mon.i, '.k', ms=3)
    axes[0].set_title('Spike Aktivitesi')
    axes[0].set_ylabel('Nöron İndeksi')
    axes[0].grid(True, linestyle='--', alpha=0.5)

    # Voltaj Plot
    if state_mon and len(state_mon.t) > 0:
        axes[1].plot(state_mon.t / ms, state_mon.v.T / mV)
    axes[1].set_title('Ortalama Membran Potansiyeli')
    axes[1].set_ylabel('Potansiyel (mV)')
    axes[1].set_xlabel('Zaman (ms)')

    plt.xlim(start_ms, end_ms)
    plt.tight_layout(rect=[0, 0, 1, 0.95])


def plot_figure2_classic(
        tones, times,
        monitors_A, monitors_B,
        thalamic_spikemon, N_input_per_tone,
        window_ms=(-50, 250), bin_ms=2, stim_ms=50, gap_ms=200,
        title="Classic oddball – Figure 2 style"
):
    """
    Figure-2 (classic oddball) yerleşimi:
      Col-1: Response to standard (A)
      Col-2: Response to deviant  (B)
      Col-3: Deviant − Standard (Δ I_syn; Δ thalamus)
    Dönüş: matplotlib.figure.Figure
    """
    import numpy as np
    import matplotlib.pyplot as plt
    from brian2 import ms, SpikeMonitor, nA, mV

    # ---------------- helpers ----------------
    def _as_ms_arr(q):
        """Brian2 nicelik/dizi -> ms cinsinden float numpy array."""
        return np.asarray((q / ms) if hasattr(q, 'unit') else q, dtype=float)

    def _get_first_attr(state_mon, names):
        for nm in names:
            if hasattr(state_mon, nm):
                return getattr(state_mon, nm)
        return None

    def _mean_trace(state_mon, t0, t1, *, prefer_currents=True, use_voltage_fallback=False):
        """
        Pencerede nöron-ort. zaman serisi (numpy float) döndürür.
        Öncelik: I_syn (nA). Yoksa ve izinliyse v (mV) fallback.
        Dönüş: (t_rel_ms [np.float], y [np.float] or None)
        """
        if state_mon is None:
            return None, None
        m = (state_mon.t >= t0) & (state_mon.t < t1)
        if not np.any(m):
            return None, None

        t_rel_ms = _as_ms_arr(state_mon.t[m] - t0)  # 0..(post-pre)

        y = None
        if prefer_currents:
            varI = _get_first_attr(state_mon, ['I_syn', 'Isyn', 'I_total', 'IALL'])
            if varI is not None:
                y = np.mean((varI[:, m] / nA), axis=0).flatten().astype(float)  # nA

        if y is None and use_voltage_fallback:
            varV = _get_first_attr(state_mon, ['v', 'V'])
            if varV is not None:
                y = np.mean((varV[:, m] / mV), axis=0).flatten().astype(float)  # mV

        return t_rel_ms, y

    def _psth_on_edges(spmon_or_tuple, t0, t1, edges_rel_ms, rate_norm=True):
        """
        t0..t1 aralığındaki spike'ları ref=t0'a göre 0 tabanlı 'edges_rel_ms' (ms) ile histogramlar.
        """
        if spmon_or_tuple is None:
            return np.zeros(len(edges_rel_ms) - 1, dtype=float)
        if isinstance(spmon_or_tuple, SpikeMonitor):
            tt = spmon_or_tuple.t
            Nn = getattr(spmon_or_tuple.source, 'N', 1)
        else:
            tt = spmon_or_tuple[0]
            Nn = None

        m = (tt >= t0) & (tt < t1)
        rel0 = _as_ms_arr(tt[m] - t0)  # 0..(post-pre)
        H, _ = np.histogram(rel0, bins=edges_rel_ms)
        H = H.astype(float)
        if rate_norm and isinstance(spmon_or_tuple, SpikeMonitor) and Nn not in (None, 0):
            H = H / (((edges_rel_ms[1] - edges_rel_ms[0]) / 1000.0) * Nn)  # Hz/nöron
        return H

    def _split_AB_inputs(spmon):
        # Hem SpikeMonitor hem de (t,i) tuple’ını destekle
        if isinstance(spmon, SpikeMonitor):
            t, i = spmon.t, spmon.i
        else:
            t, i = spmon  # (t, i) tuple
        A = (t[i < N_input_per_tone], i[i < N_input_per_tone])
        B = (t[i >= N_input_per_tone], i[i >= N_input_per_tone] - N_input_per_tone)
        return A, B

    # ---------------- verileri hazırla ----------------
    tones = np.asarray(tones)
    A_onsets = [times[i] for i in np.where(tones == 0)[0]]
    B_onsets = [times[i] for i in np.where(tones == 1)[0]]

    smP_A = monitors_A.get('statemon_p')
    smPE_A = monitors_A.get('statemon_pe')
    spP_A = monitors_A.get('spikemon_p')
    spPE_A = monitors_A.get('spikemon_pe')

    smP_B = monitors_B.get('statemon_p')
    smPE_B = monitors_B.get('statemon_pe')
    spP_B = monitors_B.get('spikemon_p')
    spPE_B = monitors_B.get('spikemon_pe')

    thA, thB = _split_AB_inputs(thalamic_spikemon)

    pre_ms, post_ms = window_ms
    window_len_ms = post_ms - pre_ms  # örn. 300 ms
    # Ortak ızgara (akımlar için) ve histogram kenarları (PSTH/Thal) — 0 tabanlı
    t_grid = np.arange(0.0, window_len_ms + bin_ms, bin_ms, dtype=float)
    edges_rel = np.arange(0.0, window_len_ms + bin_ms, bin_ms, dtype=float)
    centers = edges_rel[:-1] + bin_ms / 2.0

    # ---------------- çekirdek hesap ----------------
    def _avg_condition(onsets, smP, smPE, spP, spPE, th_tuple):
        curves = {'t_ms': t_grid.copy(), 'P_Isyn': None, 'PE_Isyn': None,
                  'rate_t': centers.copy(), 'P_rate': None, 'PE_rate': None,
                  'th_t': centers.copy(), 'th_A': None, 'th_B': None}
        if len(onsets) == 0:
            return curves

        # Akımlar için NaN-bilinçli toplayıcı
        sumP = np.zeros_like(t_grid, dtype=float);
        cntP = np.zeros_like(t_grid, dtype=int)
        sumPE = np.zeros_like(t_grid, dtype=float);
        cntPE = np.zeros_like(t_grid, dtype=int)

        acc_rP = np.zeros_like(centers, dtype=float)
        acc_rPE = np.zeros_like(centers, dtype=float)
        acc_thA = np.zeros_like(centers, dtype=float)
        acc_thB = np.zeros_like(centers, dtype=float)

        for ref in onsets:
            t0 = ref + pre_ms * ms
            t1 = ref + post_ms * ms

            # I_syn (P)
            t_rel, y = _mean_trace(smP, t0, t1, prefer_currents=True, use_voltage_fallback=False)
            if y is not None and t_rel is not None:
                y_interp = np.interp(t_grid, t_rel, y, left=np.nan, right=np.nan)
                valid = ~np.isnan(y_interp)
                sumP[valid] += y_interp[valid];
                cntP[valid] += 1

            # I_syn (PE)
            t_rel2, y2 = _mean_trace(smPE, t0, t1, prefer_currents=True, use_voltage_fallback=False)
            if y2 is not None and t_rel2 is not None:
                y2_interp = np.interp(t_grid, t_rel2, y2, left=np.nan, right=np.nan)
                valid2 = ~np.isnan(y2_interp)
                sumPE[valid2] += y2_interp[valid2];
                cntPE[valid2] += 1

            # PSTH (P ve PE) — 0 tabanlı kenarlarla
            acc_rP += _psth_on_edges(spP, t0, t1, edges_rel, rate_norm=True)
            acc_rPE += _psth_on_edges(spPE, t0, t1, edges_rel, rate_norm=True)

            # Thalamus A/B
            acc_thA += _psth_on_edges(th_tuple[0], t0, t1, edges_rel, rate_norm=False)
            acc_thB += _psth_on_edges(th_tuple[1], t0, t1, edges_rel, rate_norm=False)

        ntr = float(len(onsets))
        # Akım ortalamaları (varsa)
        curves['P_Isyn'] = None if np.all(cntP == 0) else (sumP / np.maximum(cntP, 1))
        curves['PE_Isyn'] = None if np.all(cntPE == 0) else (sumPE / np.maximum(cntPE, 1))
        # PSTH ve Thalamus ortalamaları
        curves['P_rate'] = acc_rP / ntr
        curves['PE_rate'] = acc_rPE / ntr
        curves['th_A'] = acc_thA / ntr
        curves['th_B'] = acc_thB / ntr
        return curves

    std = _avg_condition(A_onsets, smP_A, smPE_A, spP_A, spPE_A, (thA, thB))
    dev = _avg_condition(B_onsets, smP_B, smPE_B, spP_B, spPE_B, (thA, thB))

    # ---------------- çizim ----------------
    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(3, 3, hspace=0.45, wspace=0.35)
    fig.suptitle(title, fontsize=14, y=0.98)

    def _draw_column(col, head, data):
        # Üst: Prediction (I_syn)
        ax1 = fig.add_subplot(gs[0, col]);
        ax1.set_title(head)
        if data['P_Isyn'] is not None:
            ax1.plot(data['t_ms'] / 1000.0, data['P_Isyn'], lw=2)
        ax1.axvline(0, color='k', ls='--', lw=1)
        ax1.axvline(stim_ms / 1000.0, color='k', ls='--', lw=1)
        ax1.set_xlim(0, window_len_ms / 1000.0)
        ax1.set_ylabel("Synaptic currents (I_syn, nA)")

        # Orta: Prediction Error (I_syn)
        ax2 = fig.add_subplot(gs[1, col], sharex=ax1)
        if data['PE_Isyn'] is not None:
            ax2.plot(data['t_ms'] / 1000.0, data['PE_Isyn'], lw=2)
        ax2.axvline(0, color='k', ls='--', lw=1)
        ax2.axvline(stim_ms / 1000.0, color='k', ls='--', lw=1)
        ax2.set_ylabel("Synaptic currents (I_syn, nA)")
        ax2.tick_params(labelbottom=False)

        # Alt: Thalamic giriş histogramları (0 tabanlı)
        ax3 = fig.add_subplot(gs[2, col], sharex=ax1)
        w = bin_ms / 1000.0
        ax3.bar(data['th_t'] / 1000.0, data['th_A'], width=w, alpha=0.7, label='A input')
        ax3.bar(data['th_t'] / 1000.0, data['th_B'], width=w, alpha=0.5, label='B input')
        ax3.set_ylabel("Thalamic spikes")
        ax3.set_xlabel("time (s)")
        ax3.legend(fontsize=8)

    # 1) Standart
    _draw_column(0, "Response to standard", std)
    # 2) Aykırı
    _draw_column(1, "Response to deviant", dev)

    # 3) Deviant − Standard (I_syn farkı + thalamus farkı)
    axd1 = fig.add_subplot(gs[0, 2]);
    axd1.set_title("Deviant − Standard")
    axd2 = fig.add_subplot(gs[1, 2], sharex=axd1)
    axd3 = fig.add_subplot(gs[2, 2], sharex=axd1)

    if std['P_Isyn'] is not None and dev['P_Isyn'] is not None:
        axd1.plot(t_grid / 1000.0, (dev['P_Isyn'] - std['P_Isyn']), lw=2, label='P')
        axd1.axvline(0, color='k', ls='--', lw=1)
        axd1.axvline(stim_ms / 1000.0, color='k', ls='--', lw=1)
        axd1.set_ylabel("Δ I_syn (nA)");
        axd1.legend(fontsize=8)

    if std['PE_Isyn'] is not None and dev['PE_Isyn'] is not None:
        axd2.plot(t_grid / 1000.0, (dev['PE_Isyn'] - std['PE_Isyn']), lw=2, label='PE')
        axd2.axvline(0, color='k', ls='--', lw=1)
        axd2.axvline(stim_ms / 1000.0, color='k', ls='--', lw=1)
        axd2.set_ylabel("Δ I_syn (nA)");
        axd2.legend(fontsize=8)

    # Δ thalamus (0 tabanlı aynı merkezlerle)
    dA = (dev['th_A'] - std['th_A'])
    dB = (dev['th_B'] - std['th_B'])
    w = bin_ms / 1000.0
    axd3.bar(centers / 1000.0, dA, width=w, alpha=0.7, label='A input')
    axd3.bar(centers / 1000.0, dB, width=w, alpha=0.5, label='B input')
    axd3.set_ylabel("Δ thalamus");
    axd3.set_xlabel("time (s)")
    axd3.legend(fontsize=8)
    axd3.set_xlim(0, window_len_ms / 1000.0)

    return fig


def plot_figure2_classic_paperlike(
        tones, times,
        monitors_A, monitors_B,
        thalamic_spikemon,
        N_input_per_tone,
        pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50,
        bin_ms=2, smooth_ms=8,
        title="Classic oddball – Figure 2 (paper-like)",
        **_  # <-- ekle
):
    """
    Standart = A, Aykırı = B.
    P ve PE katmanlarında AMPA/NMDA/GABA (varsa) + altta firing rate (Hz/nöron).
    Sağ sütun: B − A farkı. plt.show() çağırmaz; fig döndürür.
    """
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from brian2 import ms, mV, SpikeMonitor
    from brian2.units.fundamentalunits import Quantity

    # ---------- yardımcılar ----------
    def _as_ms_arr(q):
        """
        Brian2 Quantity (skalar/vektör) veya düz sayı/diziyi
        ms cinsinden 1D float numpy array'e çevirir.
        """
        import numpy as np
        from brian2 import ms
        try:
            arr = q / ms  # Quantity ise boyutsuz sayı/dizi döner
        except Exception:
            arr = q  # Quantity değilse olduğu gibi
        arr = np.asarray(arr)
        if arr.ndim == 0:
            return np.array([float(arr)], dtype=float)
        return arr.astype(float).reshape(-1)

    def _pick_attr(obj, names):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return None

    # AMPA/NMDA/GABA: deneme başına, nöron başına; pre-stim baseline (mV eq.)
    def _currents_components_avg_baseline(onsets, statemon, pre_ms, post_ms, bin_ms, smooth_ms=0):
        """
        AMPA/NMDA/GABA (varsa) bileşenlerini ayrı hesaplar; yoksa I_syn'e düşer.
        Deneme başına, nöron başına; pre-stim baseline (mV eq.). 0..T grid döner.
        NaN güvenli: veri olmayan denemeleri atlar, kısmi NaN'leri ağırlıklı ortalar.
        """
        import numpy as np
        from brian2 import ms, mV

        if statemon is None or len(onsets) == 0:
            return None, None

        def _pick_attr(obj, names):
            for n in names:
                if hasattr(obj, n):
                    return getattr(obj, n)
            return None

        t_stat = statemon.t
        T = post_ms - pre_ms
        grid = np.arange(0.0, T + bin_ms, bin_ms, dtype=float)

        # Bileşenleri topla (None olanları ele)
        comps = {
            "AMPA": _pick_attr(statemon, ["I_ampa", "IAMPA", "I_AMPA"]),
            "NMDA": _pick_attr(statemon, ["I_nmda", "INMDA", "I_NMDA"]),
            "GABA": _pick_attr(statemon, ["I_gaba", "IGABA", "I_GABA"]),
        }
        comps = {k: v for k, v in comps.items() if v is not None}
        if not comps:
            Isyn = _pick_attr(statemon, ["I_syn", "Isyn", "I_total", "IALL"])
            if Isyn is None:
                return None, None
            comps = {"I_syn": Isyn}

        pre_abs = abs(pre_ms)
        out = {}

        for name, I in comps.items():
            # (nöron, zaman) şekline zorla ve mV eşdeğeri yap
            I_mV = (I / mV).astype(float)
            if I_mV.ndim == 2 and I_mV.shape[1] != len(t_stat):
                I_mV = I_mV.T

            acc = np.zeros_like(grid, dtype=float)
            cnt = np.zeros_like(grid, dtype=int)

            for ref in onsets:
                t0 = ref + pre_ms * ms
                t1 = ref + post_ms * ms
                mseg = (t_stat >= t0) & (t_stat < t1)
                if not np.any(mseg):
                    continue

                t_rel = np.asarray((t_stat[mseg] - t0) / ms, dtype=float).reshape(-1)
                seg = I_mV[:, mseg]  # (nöron, zaman_seg)

                # pre-stim baseline (nöron başına)
                pre_mask = (t_rel < pre_abs)
                if not np.any(pre_mask):
                    continue
                base = np.nanmean(seg[:, pre_mask], axis=1, keepdims=True)
                seg = seg - np.nan_to_num(base, nan=0.0)

                # grid'e interpolate → (nöron, grid)
                yi = np.empty((seg.shape[0], grid.size), dtype=float);
                yi[:] = np.nan
                for n in range(seg.shape[0]):
                    yi[n] = np.interp(grid, t_rel, seg[n], left=np.nan, right=np.nan)

                # NaN güvenli nöron ortalaması (bin bazında ağırlıklı)
                mask = np.isfinite(yi)
                counts = mask.sum(axis=0)
                if counts.max() == 0:
                    # bu denemede tüm grid boş → atla
                    continue
                sums = np.nansum(yi, axis=0)
                y = np.divide(sums, counts, out=np.full_like(sums, np.nan), where=counts > 0)

                ok = np.isfinite(y)
                acc[ok] += y[ok]
                cnt[ok] += 1

            # Denemeler ortalaması (NaN olan grid noktaları 0 sayılmaz)
            y_mean = np.divide(acc, cnt, out=np.zeros_like(acc), where=cnt > 0)

            if smooth_ms and smooth_ms > 0:
                k = max(1, int(round(smooth_ms / bin_ms)))
                ker = np.ones(k) / k
                y_mean = np.convolve(y_mean, ker, mode='same')

            out[name] = y_mean

        return grid, out

    # PSTH → Hz (deneme başına, opsiyonel nöron başına)
    def _psth_rate_hz(onsets, spmon_or_tuple, pre_ms, post_ms, bin_ms, smooth_ms=0, per_neuron=True):
        import numpy as np
        from brian2 import ms, SpikeMonitor

        T = post_ms - pre_ms
        edges = np.arange(0.0, T + bin_ms, bin_ms, dtype=float)
        centers = edges[:-1] + bin_ms / 2.0

        if isinstance(spmon_or_tuple, SpikeMonitor):
            t_all, i_all = spmon_or_tuple.t, spmon_or_tuple.i
            Nn = getattr(spmon_or_tuple.source, "N", 1)
        else:
            t_all, i_all = spmon_or_tuple
            Nn = None

        try:
            t_all_ms = np.asarray(t_all / ms, dtype=float).reshape(-1)
        except Exception:
            t_all_ms = np.asarray(t_all, dtype=float).reshape(-1)
        H, ntr = np.zeros(len(edges) - 1, dtype=float), 0

        for ref in onsets:
            t0 = float((ref + pre_ms * ms) / ms)
            t1 = float((ref + post_ms * ms) / ms)
            m = (t_all_ms >= t0) & (t_all_ms < t1)
            rel = t_all_ms[m] - t0
            H += np.histogram(rel, bins=edges)[0]
            ntr += 1

        if ntr == 0:
            return centers, np.zeros_like(centers)

        H = H / ntr
        rate = H / (bin_ms / 1000.0)  # Hz
        if per_neuron and Nn not in (None, 0):
            rate = rate / max(int(Nn), 1)

        if smooth_ms and smooth_ms > 0:
            k = max(1, int(round(smooth_ms / bin_ms)))
            ker = np.ones(k) / k
            rate = np.convolve(rate, ker, mode='same')

        return centers, rate

    def _plot_comps(ax, grid, comp_dict, color):
        # Solid: AMPA, Dashed: NMDA, Dotted: GABA
        styles = {'AMPA': '-', 'NMDA': '--', 'GABA': ':', 'I_syn': '-'}
        for k, v in comp_dict.items():
            ax.plot(grid / 1000.0, v, styles.get(k, '-'), color=color, lw=2.0, label=k)

    # ---------- A (standart) ve B (aykırı) onset listeleri ----------
    tones_arr = np.asarray(tones)
    A_onsets = [times[i] for i in np.where(tones_arr == 0)[0]]
    B_onsets = [times[i] for i in np.where(tones_arr == 1)[0]]

    # ---------- akım ve rate eğrilerini çıkar ----------
    # P katmanı
    gP_A, P_A = _currents_components_avg_baseline(A_onsets, monitors_A.get('statemon_p'), -pre_ms, post_ms, bin_ms,
                                                  smooth_ms)
    _, P_B = _currents_components_avg_baseline(B_onsets, monitors_A.get('statemon_p'), -pre_ms, post_ms, bin_ms,
                                               smooth_ms)
    gP2_A, P2_A = _currents_components_avg_baseline(A_onsets, monitors_B.get('statemon_p'), -pre_ms, post_ms, bin_ms,
                                                    smooth_ms)
    _, P2_B = _currents_components_avg_baseline(B_onsets, monitors_B.get('statemon_p'), -pre_ms, post_ms, bin_ms,
                                                smooth_ms)

    cP_A, rP_A = _psth_rate_hz(A_onsets, monitors_A.get('spikemon_p'), -pre_ms, post_ms, bin_ms, smooth_ms,
                               per_neuron=True)
    _, rP_B = _psth_rate_hz(B_onsets, monitors_A.get('spikemon_p'), -pre_ms, post_ms, bin_ms, smooth_ms,
                            per_neuron=True)
    _, rP2_A = _psth_rate_hz(A_onsets, monitors_B.get('spikemon_p'), -pre_ms, post_ms, bin_ms, smooth_ms,
                             per_neuron=True)
    _, rP2_B = _psth_rate_hz(B_onsets, monitors_B.get('spikemon_p'), -pre_ms, post_ms, bin_ms, smooth_ms,
                             per_neuron=True)

    # PE katmanı
    gPE_A, PE_A = _currents_components_avg_baseline(A_onsets, monitors_A.get('statemon_pe'), -pre_ms, post_ms, bin_ms,
                                                    smooth_ms)
    _, PE_B = _currents_components_avg_baseline(B_onsets, monitors_A.get('statemon_pe'), -pre_ms, post_ms, bin_ms,
                                                smooth_ms)
    gPE2_A, PE2_A = _currents_components_avg_baseline(A_onsets, monitors_B.get('statemon_pe'), -pre_ms, post_ms, bin_ms,
                                                      smooth_ms)
    _, PE2_B = _currents_components_avg_baseline(B_onsets, monitors_B.get('statemon_pe'), -pre_ms, post_ms, bin_ms,
                                                 smooth_ms)

    cPE_A, rPE_A = _psth_rate_hz(A_onsets, monitors_A.get('spikemon_pe'), -pre_ms, post_ms, bin_ms, smooth_ms,
                                 per_neuron=True)
    _, rPE_B = _psth_rate_hz(B_onsets, monitors_A.get('spikemon_pe'), -pre_ms, post_ms, bin_ms, smooth_ms,
                             per_neuron=True)
    _, rPE2_A = _psth_rate_hz(A_onsets, monitors_B.get('spikemon_pe'), -pre_ms, post_ms, bin_ms, smooth_ms,
                              per_neuron=True)
    _, rPE2_B = _psth_rate_hz(B_onsets, monitors_B.get('spikemon_pe'), -pre_ms, post_ms, bin_ms, smooth_ms,
                              per_neuron=True)

    # Talamik giriş: A panelinde A girişi, B panelinde B girişi
    thA = (thalamic_spikemon.t[thalamic_spikemon.i < N_input_per_tone],
           thalamic_spikemon.i[thalamic_spikemon.i < N_input_per_tone])
    thB = (thalamic_spikemon.t[thalamic_spikemon.i >= N_input_per_tone],
           thalamic_spikemon.i[thalamic_spikemon.i >= N_input_per_tone] - N_input_per_tone)
    cTH_A, rTH_A = _psth_rate_hz(A_onsets, thA, -pre_ms, post_ms, bin_ms, smooth_ms, per_neuron=True)
    _, rTH_B = _psth_rate_hz(B_onsets, thB, -pre_ms, post_ms, bin_ms, smooth_ms, per_neuron=True)

    # farklar (B − A)
    def _diff_dict(B, A):
        if B is None or A is None: return None
        keys = sorted(set(B.keys()) | set(A.keys()))
        return {k: (B.get(k, 0) - A.get(k, 0)) for k in keys}

    P_DIFF = _diff_dict(P_B, P_A)
    PE_DIFF = _diff_dict(PE_B, PE_A)
    rP_DIFF = (rP_B - rP_A)
    rPE_DIFF = (rPE_B - rPE_A)
    rTH_DIFF = (rTH_B - rTH_A)

    # ---------- çizim ----------
    fig = plt.figure(figsize=(14, 9), layout="constrained")
    fig.suptitle(title, fontsize=14)
    G = fig.add_gridspec(3, 3, hspace=0.25, wspace=0.25, left=0.07, right=0.98, top=0.92, bottom=0.08)

    def _cell_with_rate(row, col):
        sg = G[row, col].subgridspec(2, 1, height_ratios=[3, 1.8], hspace=0.08)
        axC = fig.add_subplot(sg[0, 0]);
        axR = fig.add_subplot(sg[1, 0], sharex=axC)
        return axC, axR

    axP_A_c, axP_A_r = _cell_with_rate(0, 0)  # P – A (standard)
    axP_B_c, axP_B_r = _cell_with_rate(0, 1)  # P – B (deviant)
    axP_D_c, axP_D_r = _cell_with_rate(0, 2)  # P – diff

    axPE_A_c, axPE_A_r = _cell_with_rate(1, 0)  # PE – A
    axPE_B_c, axPE_B_r = _cell_with_rate(1, 1)  # PE – B
    axPE_D_c, axPE_D_r = _cell_with_rate(1, 2)  # PE – diff

    axTH_A = fig.add_subplot(G[2, 0])
    axTH_B = fig.add_subplot(G[2, 1])
    axTH_D = fig.add_subplot(G[2, 2])

    def _stim_mark(ax):
        ax.axvspan(0 / 1000, stim_ms / 1000, color='0.92')
        ax.axvspan(gap_ms / 1000, (gap_ms + stim_ms) / 1000, color='0.92')
        ax.axvline(0, color='0.65', ls='--', lw=1)
        ax.axvline(gap_ms / 1000.0, color='0.65', ls='--', lw=1)

    # P – A / B / diff
    if P_A is not None:
        _plot_comps(axP_A_c, gP_A, P_A, color='tab:red')  # A-coded (kırmızı)
        if P2_A is not None:
            _plot_comps(axP_A_c, gP2_A, P2_A, color='tab:blue')  # B-coded (mavi)
    if P_B is not None:
        _plot_comps(axP_B_c, gP_A, P_B, color='tab:red')
        if P2_B is not None:
            _plot_comps(axP_B_c, gP2_A, P2_B, color='tab:blue')
    if P_DIFF is not None:
        _plot_comps(axP_D_c, gP_A, P_DIFF, color='tab:green')

    axP_A_r.plot(cP_A / 1000.0, rP_A, label='A-coded', color='tab:red')
    axP_A_r.plot(cP_A / 1000.0, rP2_A, label='B-coded', color='tab:blue')
    axP_B_r.plot(cP_A / 1000.0, rP_B, label='A-coded', color='tab:red')
    axP_B_r.plot(cP_A / 1000.0, rP2_B, label='B-coded', color='tab:blue')
    axP_D_r.plot(cP_A / 1000.0, rP_DIFF, color='tab:green')

    # PE – A / B / diff
    if PE_A is not None:
        _plot_comps(axPE_A_c, gPE_A, PE_A, color='tab:red')
        if PE2_A is not None:
            _plot_comps(axPE_A_c, gPE2_A, PE2_A, color='tab:blue')
    if PE_B is not None:
        _plot_comps(axPE_B_c, gPE_A, PE_B, color='tab:red')
        if PE2_B is not None:
            _plot_comps(axPE_B_c, gPE2_A, PE2_B, color='tab:blue')
    if PE_DIFF is not None:
        _plot_comps(axPE_D_c, gPE_A, PE_DIFF, color='tab:green')

    axPE_A_r.plot(cPE_A / 1000.0, rPE_A, label='A-coded', color='tab:red')
    axPE_A_r.plot(cPE_A / 1000.0, rPE2_A, label='B-coded', color='tab:blue')
    axPE_B_r.plot(cPE_A / 1000.0, rPE_B, label='A-coded', color='tab:red')
    axPE_B_r.plot(cPE_A / 1000.0, rPE2_B, label='B-coded', color='tab:blue')
    axPE_D_r.plot(cPE_A / 1000.0, rPE_DIFF, color='tab:green')

    # Thalamus – A / B / diff
    axTH_A.plot(cTH_A / 1000.0, rTH_A, color='tab:orange', label='A input')
    axTH_B.plot(cTH_A / 1000.0, rTH_B, color='tab:orange', label='B input')
    axTH_D.plot(cTH_A / 1000.0, rTH_DIFF, color='tab:green')

    # görünüm
    for ax in [axP_A_c, axP_B_c, axP_D_c, axPE_A_c, axPE_B_c, axPE_D_c]:
        _stim_mark(ax)
        ax.set_ylabel("Synaptic currents (mV eq.)")

    for ax in [axP_A_r, axP_B_r, axP_D_r, axPE_A_r, axPE_B_r, axPE_D_r, axTH_A, axTH_B, axTH_D]:
        _stim_mark(ax)
        ax.set_xlabel("time (s)")
        ax.set_ylabel("Firing rate (Hz)")

    axP_A_c.set_title("Response to standard (A)")
    axP_B_c.set_title("Response to deviant (B)")
    axP_D_c.set_title("Deviant − Standard")

    # Bileşen lejandı
    comp_handles = [
        Line2D([0], [0], color='k', lw=2, ls='-', label='AMPA'),
        Line2D([0], [0], color='k', lw=2, ls='--', label='NMDA'),
        Line2D([0], [0], color='k', lw=2, ls=':', label='GABA'),
    ]
    axPE_D_c.legend(handles=comp_handles, loc='lower right', title="Synaptic components", fontsize=8)

    # A/B-coded legend
    axP_A_r.legend(loc='upper right', fontsize=8)
    axP_B_r.legend(loc='upper right', fontsize=8)

    # x-limitleri hizala
    total_ms = pre_ms + stim_ms + gap_ms + stim_ms + post_ms
    xlim_s = ((-pre_ms) / 1000.0, (total_ms - pre_ms) / 1000.0)
    for ax in [axP_A_c, axP_B_c, axP_D_c,
               axPE_A_c, axPE_B_c, axPE_D_c,
               axP_A_r, axP_B_r, axP_D_r,
               axPE_A_r, axPE_B_r, axPE_D_r,
               axTH_A, axTH_B, axTH_D]:
        ax.set_xlim(xlim_s)

    return fig


def plot_I_syn_multi(statemon, layer_name="PE Layer", n_neurons=10, to_mV=True):
    """
    Bir StateMonitor'dan seçilen nöronların (varsayılan 10) I_syn değerlerini çizer.
    plt.show() çağırmaz; fig döndürür.

    Parameters
    ----------
    statemon : StateMonitor
        Örn. column_A['statemon_pe'] / column_A['statemon_p'] vb.
    layer_name : str
        Başlıkta görünecek isim
    n_neurons : int
        Kaç nöron çizilecek
    to_mV : bool
        I_syn birimini mV eşdeğerinde göstermek için True (modelde volt cinsinden tutuluyorsa önerilir)

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    import numpy as np
    import matplotlib.pyplot as plt

    if not hasattr(statemon, 'I_syn'):
        raise ValueError("StateMonitor 'I_syn' kaydetmiyor. Lütfen StateMonitor'u ['v','I_syn'] ile oluştur.")

    t = statemon.t / ms
    total_neurons = statemon.I_syn.shape[0]
    n_neurons = min(n_neurons, total_neurons)

    fig, axes = plt.subplots(n_neurons, 1, figsize=(12, 2 * n_neurons), sharex=True)
    if n_neurons == 1:
        axes = [axes]

    scale = (mV if to_mV else 1.0)
    ylab = "I_syn (mV eşdeğer)" if to_mV else "I_syn (model birimi)"

    for idx in range(n_neurons):
        y = statemon.I_syn[idx] / scale
        axes[idx].plot(t, y, alpha=0.9)
        axes[idx].set_ylabel(f"Nöron {idx}")
        if idx == 0:
            axes[idx].set_title(f"{layer_name} - İlk {n_neurons} nöron için I_syn")
    axes[-1].set_xlabel("Zaman (ms)")

    fig.tight_layout()
    return fig


# ==== Thalamic vs Memory: tetikleme denetimi + görselleştirme ====
def check_chain_triggers(spikemon_mem_e, tones, times, SOA, chain_delay,
                         module_name="A", window=None, slope_tol=0.5):
    """
    Her uyaran (times[i]) sonrası memory zincirinin tetiklenip tetiklenmediğini denetler.
    - window: tetik arama penceresi; verilmezse 0.5*SOA
    - expected_slope = 1/(chain_delay/ms) (idx/ms)  ~ zincir hızı
    Dönüş: (summary, rows)
      summary: genel istatistikler
      rows   : her uyaran için {triggered, latency_ms, start_i, slope_idx_per_ms, ...}
    """
    from brian2 import ms
    import numpy as np

    if window is None:
        window = 0.5 * SOA

    t_all = spikemon_mem_e.t
    i_all = spikemon_mem_e.i

    expected_slope = 1.0 / (chain_delay / ms)  # index / ms
    rows = []
    triggered = 0
    latencies = []

    for k, (tone, t0) in enumerate(zip(tones, times)):
        w0, w1 = t0, t0 + window
        m = (t_all >= w0) & (t_all < w1)
        if not np.any(m):
            rows.append({
                "stim_idx": k, "tone": int(tone), "t0_ms": float(t0 / ms),
                "triggered": False, "latency_ms": None, "start_i": None,
                "slope_idx_per_ms": None, "slope_ok": None
            })
            continue

        t_win = np.asarray(t_all[m] / ms, dtype=float)
        i_win = np.asarray(i_all[m], dtype=int)

        order = np.argsort(t_win)
        t_win = t_win[order]
        i_win = i_win[order]

        t_first = t_win[0]
        i_first = i_win[0]
        lat = float(t_first - (t0 / ms))

        # zincir hızı ~ doğrusal eğim (idx/ms). En az 2 nokta varsa hesapla.
        if len(t_win) >= 3:
            x = t_win - t_first
            y = i_win - i_first
            try:
                slope = np.polyfit(x, y, 1)[0]
            except Exception:
                slope = (i_win[-1] - i_first) / max(1e-9, (t_win[-1] - t_first))
        elif len(t_win) >= 2:
            slope = (i_win[-1] - i_first) / max(1e-9, (t_win[-1] - t_first))
        else:
            slope = np.nan

        ok_slope = (abs(slope - expected_slope) <= slope_tol * expected_slope) if np.isfinite(slope) else None

        rows.append({
            "stim_idx": k, "tone": int(tone), "t0_ms": float(t0 / ms),
            "triggered": True, "latency_ms": lat, "start_i": int(i_first),
            "slope_idx_per_ms": float(slope) if np.isfinite(slope) else None,
            "slope_ok": bool(ok_slope) if ok_slope is not None else None
        })
        triggered += 1
        latencies.append(lat)

    n = len(times)
    summary = {
        "module": module_name,
        "N_stimuli": n,
        "triggered_count": triggered,
        "missed_count": n - triggered,
        "trigger_rate_%": 100.0 * triggered / n if n else 0.0,
        "mean_latency_ms": float(np.mean(latencies)) if latencies else None,
        "median_latency_ms": float(np.median(latencies)) if latencies else None,
        "expected_slope_idx_per_ms": float(expected_slope)
    }
    return summary, rows


def report_missed(rows):
    """Kaçan tetiklemeleri konsola kısaca raporlar."""
    missed = [r for r in rows if not r.get("triggered", False)]
    if not missed:
        print("Tüm uyaranlar zinciri tetikledi.")
        return
    print(f"Kaçan uyaran sayısı: {len(missed)}")
    print("İndeksler:", [m['stim_idx'] for m in missed])


def plot_input_vs_memory(side_label,
                         spikemon_input, N_input_per_tone,
                         spikemon_mem_e,
                         tones, times, SOA, chain_delay,
                         window=None):
    """
    Thalamic giriş ile memory zincirini alt alta raster olarak çizer;
    her uyaran için tetiklenme (✓/✗), latency ve zincirin başlangıcı işaretlenir.
    side_label: 'A' (standart) ya da 'B' (aykırı)
    """
    from brian2 import ms
    import numpy as np
    import matplotlib.pyplot as plt

    # Thalamus A/B ayır
    if side_label.upper() == 'A':
        mask_in = spikemon_input.i < N_input_per_tone
        i_in_offset = 0
        tone_val = 0
    else:
        mask_in = spikemon_input.i >= N_input_per_tone
        i_in_offset = N_input_per_tone
        tone_val = 1

    t_in = spikemon_input.t[mask_in]
    i_in = spikemon_input.i[mask_in] - i_in_offset

    tone_mask = (tones == tone_val)
    tones_sel = tones[tone_mask]
    times_sel = times[tone_mask]

    if window is None:
        window = SOA

    # Memory zinciri tetik analizini yap
    summary, rows = check_chain_triggers(
        spikemon_mem_e, tones_sel, times_sel,
        SOA=SOA, chain_delay=chain_delay,
        module_name=side_label, window=window
    )

    # Çizim
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(12, 5), sharex=True)
    fig.suptitle(f"{side_label} – Thalamic vs Memory", y=0.98)

    # Üst: Thalamic raster
    ax_top.plot(t_in / ms, i_in, '.k', ms=3)
    ax_top.set_ylabel("Thalamic Girdi")
    ax_top.grid(True, alpha=0.3, linestyle='--')
    for t0 in times_sel:
        ax_top.axvline(t0 / ms, linewidth=0.6, alpha=0.3)

    # Alt: Memory raster
    ax_bot.plot(spikemon_mem_e.t / ms, spikemon_mem_e.i, '.k', ms=2)
    ax_bot.set_ylabel("Memory (E_chain)")
    ax_bot.set_xlabel("Zaman (ms)")
    ax_bot.grid(True, alpha=0.3, linestyle='--')

    # Olay işaretleri (tetik ✓, kaçan ✗, latency başlangıcı ▼)
    for r in rows:
        x = float(r["t0_ms"])
        if r["triggered"]:
            ax_top.text(x, -2, "✓", ha='center', va='top', fontsize=9)
            x_start = r["t0_ms"] + (r["latency_ms"] or 0.0)
            ax_bot.plot([x_start], [0], marker='v', markersize=5)
        else:
            ax_top.text(x, -2, "✗", ha='center', va='top', fontsize=9, color='crimson')

    ax_top.set_title(
        f"Triggers: {summary['triggered_count']}/{summary['N_stimuli']} "
        f"({summary['trigger_rate_%']:.1f}%), mean lat: "
        f"{(summary['mean_latency_ms'] or float('nan')):.1f} ms "
        f"| exp slope: {summary['expected_slope_idx_per_ms']:.2f} idx/ms",
        fontsize=10
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    return summary, rows


def run_single_simulation(paradigm_name, paradigm_params, model_params, stimulus_amplitude, seed_value):
    """
    Her çalıştırmada temiz bir başlangıç yapan, tamamen bağımsız ve kararlı
    nihai simülasyon fonksiyonu. BU VERSİYON "NaN KAPANI" İÇERMEKTEDİR.
    """

    spikemon_p_A = spikemon_pe_A = statemon_p_A = statemon_pe_A = None
    spikemon_p_B = spikemon_pe_B = statemon_p_B = statemon_pe_B = None
    spikemon_input = None
    syn_memA_to_PA = syn_memA_to_PB = syn_memB_to_PB = syn_memB_to_PA = None
    N_input_per_tone = None

    all_interactive_widgets = {} # Tüm widget'ları burada toplayacağız

    print("\n" + "#" * 70)
    print(f"### TEK AŞAMALI SİMÜLASYON BAŞLATILIYOR: {paradigm_name.upper()} (SEED: {seed_value}) ###")
    print("### MOD: NaN HATASI AVcısı AKTİF ###")
    print("#" * 70 + "\n")

    # Geçici dosyalar için D sürücüsünü kullan ve derlemeyi net.run'a bırak
    temp_dir = 'D:/brian2_temp'
    set_device('cpp_standalone', directory=temp_dir)

    start_scope()
    dt = 0.05 * ms
    defaultclock.dt = dt
    seed(seed_value)

    # Nöron sayıları ve sabitler
    N_input_per_tone = 10
    N_input_total = N_input_per_tone * 2
    STIMULUS_DURATION = 10 * ms
    N_EXC = model_params['N_EXC'];
    N_INH = model_params['N_INH']
    N_E_MEM = model_params['N_E_MEM'];
    N_I_MEM = model_params['N_I_MEM']

    # Paradigma ve girdi akımını oluştur
    tones, times = create_paradigm_sequence(paradigm_name, paradigm_params)
    soa_or_isi = paradigm_params.get('soa', paradigm_params.get('isi', 200 * ms))
    total_duration = times[-1] + soa_or_isi * 2
    print(f"Simülasyon '{paradigm_name}' paradigması ile {total_duration} boyunca çalışacak.")

    # --- AKILLI TimedArray KULLANIMI (BELLEK SORUNUNU ÖNLEMEK İÇİN) ---
    stimulus_dt = 1 * ms  # Uyaran için kaba zaman adımı
    total_duration_steps = int(total_duration / stimulus_dt)
    current_arr = np.zeros((total_duration_steps, N_input_total))

    for t_stim, tone_type in zip(times, tones):
        start_idx = int(t_stim / stimulus_dt)
        end_idx = int((t_stim + STIMULUS_DURATION) / stimulus_dt)
        neuron_start = int(tone_type * N_input_per_tone)
        neuron_end = neuron_start + N_input_per_tone
        if end_idx < total_duration_steps:
            current_arr[start_idx:end_idx, neuron_start:neuron_end] = stimulus_amplitude

    stimulus_current = TimedArray(current_arr * mV, dt=stimulus_dt, name='stimulus_current')

    # --- TON KAPILARI (A/B) ---
    gate_dt = stimulus_dt
    n_steps = total_duration_steps
    gateA = np.zeros(n_steps)
    gateB = np.zeros(n_steps)
    gate_ALL = np.zeros(n_steps)  # <-- YENİ SATIR
    GATE_PRE = 5 * ms
    GATE_WIN = STIMULUS_DURATION + 20 * ms
    for t_stim, tone_type in zip(times, tones):
        start = max(0, int((t_stim - GATE_PRE) / gate_dt))
        end = min(n_steps, int((t_stim + GATE_WIN) / gate_dt))
        gate_ALL[start:end] = 1.0  # <-- YENİ SATIR: Her tonda bu kapıyı aç
        if tone_type == 0:
            gateA[start:end] = 1.0
        else:
            gateB[start:end] = 1.0

    tone_gate_A = TimedArray(gateA, dt=gate_dt, name='tone_gate_A')
    tone_gate_B = TimedArray(gateB, dt=gate_dt, name='tone_gate_B')
    tone_gate_ALL = TimedArray(gate_ALL, dt=gate_dt, name='tone_gate_ALL')  # <-- YENİ SATIR

    # --- TON MARKER'LARI (her tonda 1 deterministik olay) ---
    times_A_evt = times[tones == 0] + 1 * ms
    times_B_evt = times[tones == 1] + 1 * ms
    tone_trig_A = SpikeGeneratorGroup(1, indices=np.zeros(len(times_A_evt), dtype=int),
                                      times=times_A_evt, name='tone_trig_A')
    tone_trig_B = SpikeGeneratorGroup(1, indices=np.zeros(len(times_B_evt), dtype=int),
                                      times=times_B_evt, name='tone_trig_B')

    # --- AKILLI TimedArray SONU ---

    # Ağ bileşenleri ve TÜM monitörleri oluştur
    ThalamicInput = create_neuron_group(N_input_total, 'ThalamicInput', 'input', model_params['input'])
    column_A = create_cortical_column('A', N_EXC, N_INH, model_params['exc'], model_params['inh'],
                                      model_params['syn_weights'], record_states=True)
    column_B = create_cortical_column('B', N_EXC, N_INH, model_params['exc'], model_params['inh'],
                                      model_params['syn_weights'], record_states=True)
    new_w_PEP = 'clip(10.0 + sqrt(0.1 * 10.0) * randn(), 0, 40.0)'

    column_A['syn_PE_P'].w = new_w_PEP
    column_B['syn_PE_P'].w = new_w_PEP
    # --- Basit LIF bellek zinciri ---
    USE_SIMPLE_MEMORY = True
    SIMPLE_MEM_PARAMS = dict(
        theta=1.0, v_reset=0.0, v_rest=0.0,
        tau_m=20 * ms, t_ref=50 * ms,
        J_ff=1.1,  # zincir içi ileri iletme büyüklüğü
        d_ff=6 * ms,  # 400*1.5ms ≈ 600ms zincir süresi
        J_in=15.0,  # zinciri başlatan girdi büyüklüğü
        tau_gate=20 * ms  # kapı toparlanma süresi
    )
    N_E_MEM = model_params['N_E_MEM']  # mevcut parametrelerini kullan
    if USE_SIMPLE_MEMORY:
        memory_module_A = create_simple_memory_module('A', SIMPLE_MEM_PARAMS, N_E_MEM)
        memory_module_B = create_simple_memory_module('B', SIMPLE_MEM_PARAMS, N_E_MEM)
    else:
        memory_module_A = create_memory_module('A', model_params['mem_all'], N_E_MEM, N_I_MEM)
        memory_module_B = create_memory_module('B', model_params['mem_all'], N_E_MEM, N_I_MEM)

    thalamic_statemon = StateMonitor(ThalamicInput, 'v', record=range(min(10, N_input_total)), dt=1 * ms,
                                     name='statemon_thalamic')

    # Statik ve Plastik sinapsları oluştur
    delay_str = 'rand()*15*ms';
    on_pre_exc = 's_ampa_post = s_ampa_post + w; x_nmda_post = x_nmda_post + w * 0.2';
    w_p_to_mem = 10
    syn_Thalamic_PE_A = create_synaptic_connection(ThalamicInput, column_A['PE'], 0.9,
                                                   model_params['syn_weights']["w_EE"], on_pre_exc,
                                                   delay_model=delay_str, cond=f'i < {N_input_per_tone}')
    syn_Thalamic_PE_B = create_synaptic_connection(ThalamicInput, column_B['PE'], 0.9,
                                                   model_params['syn_weights']["w_EE"], on_pre_exc,
                                                   delay_model=delay_str, cond=f'i >= {N_input_per_tone}')
    # P → Memory (kapılı tek-atımlık tetik)
    U = 1.0
    # ---------------------------------------------------------
    # DÜZELTİLMİŞ SİNAPS BLOĞU: KAPILI P TETİKLEMESİ (GATED TRIGGER)
    # ---------------------------------------------------------
    # Sorun: P katmanı sessizlikte bile hafızayı tetikliyor.
    # Çözüm: P -> Bellek bağlantısını, 'tone_gate' ile çarpıyoruz.
    # Böylece sadece ses varken P'nin sözü geçiyor.

    J_IN_VAL = float(SIMPLE_MEM_PARAMS['J_in'])

    # 1. P Katmanı -> Bellek (GATED)
    # Formül: v += w * J_IN * tone_gate(t)
    # tone_gate(t): Ses varken 1.0, yokken 0.0 olan fonksiyondur.

    syn_P_to_Mem_A = Synapses(
        column_A['P'], memory_module_A['E_chain'], model='w:1',
        on_pre=f'v_post += w * {J_IN_VAL} * tone_gate_A(t)',  # KAPILI TETİK
        name='trig_A'
    )
    syn_P_to_Mem_A.connect(condition='j==0')
    syn_P_to_Mem_A.w = 1.0  # P ne kadar kuvvetliyse o kadar etkilesin
    syn_P_to_Mem_A.delay = delay_str

    syn_P_to_Mem_B = Synapses(
        column_B['P'], memory_module_B['E_chain'], model='w:1',
        on_pre=f'v_post += w * {J_IN_VAL} * tone_gate_B(t)',  # KAPILI TETİK
        name='trig_B'
    )
    syn_P_to_Mem_B.connect(condition='j==0')
    syn_P_to_Mem_B.w = 1.0
    syn_P_to_Mem_B.delay = delay_str

    # 2. Tone Trigger -> Bellek (İPTAL)
    syn_Tone_to_Mem_A = Synapses(
        tone_trig_A, memory_module_A['E_chain'], model='w:1',
        on_pre=f'v_post += w * {J_IN_VAL}', name='trig_tone_A'
    )
    syn_Tone_to_Mem_A.connect(False)

    syn_Tone_to_Mem_B = Synapses(
        tone_trig_B, memory_module_B['E_chain'], model='w:1',
        on_pre=f'v_post += w * {J_IN_VAL}', name='trig_tone_B'
    )
    syn_Tone_to_Mem_B.connect(False)

    # 3. Thalamus -> Bellek (İPTAL)
    syn_Thal_to_Mem_A = Synapses(
        ThalamicInput, memory_module_A['E_chain'], model='w:1',
        on_pre=f'v_post += w * {J_IN_VAL}', name='trig_thal_A'
    )
    syn_Thal_to_Mem_A.connect(False)

    syn_Thal_to_Mem_B = Synapses(
        ThalamicInput, memory_module_B['E_chain'], model='w:1',
        on_pre=f'v_post += w * {J_IN_VAL}', name='Thal_to_Mem_B'
    )
    syn_Thal_to_Mem_B.connect(False)

    initial_weights = {};
    synapse_map = {};
    conn_prob = 1.0


    def create_deterministic_connections(N_source, N_target, prob):
        n_synapses = int(N_source * N_target * prob)
        i = np.random.randint(0, N_source, size=n_synapses);
        j = np.random.randint(0, N_target, size=n_synapses)
        return {'i': i, 'j': j}

    # PLASTİSİTE AÇIK OLMALI!
    plasticity_is_on = True

    mu = 0.4
    sigma = mu * 0.20  # 0.08
    W_MIN_INIT, W_MAX_INIT = 0.01, 10.0  # üst sınırı kendi modeline göre koy

    conn_A_A = create_deterministic_connections(N_E_MEM, N_EXC, conn_prob)
    w_init_A_A = np.clip(mu + sigma*np.random.randn(len(conn_A_A['i'])), W_MIN_INIT, W_MAX_INIT)
    initial_weights['A_A'] = np.copy(w_init_A_A)
    syn_Mem_to_P_A = create_stdp_synapse(
        memory_module_A['E_chain'], column_A['P'], w_init_A_A,
        conn_data=conn_A_A, delay_model=delay_str,
        A_plus=0.02, A_minus=-0.03, taupre_ms=12.0, taupost_ms=24.0,
        multiplicative=True, name='stdp_AA'
    )
    synapse_map['A_A'] = syn_Mem_to_P_A
    conn_B_B = create_deterministic_connections(N_E_MEM, N_EXC, conn_prob)
    w_init_B_B = np.clip(mu + sigma*np.random.randn(len(conn_B_B['i'])), W_MIN_INIT, W_MAX_INIT)
    initial_weights['B_B'] = np.copy(w_init_B_B)
    syn_Mem_to_P_B = create_stdp_synapse(
        memory_module_B['E_chain'], column_B['P'], w_init_B_B,
        conn_data=conn_B_B, delay_model=delay_str,
        A_plus = 0.02, A_minus = -0.03, taupre_ms = 12.0, taupost_ms = 24.0,
        multiplicative = True, name = 'stdp_BB'
    )
    synapse_map['B_B'] = syn_Mem_to_P_B
    conn_A_B = create_deterministic_connections(N_E_MEM, N_EXC, conn_prob)
    w_init_A_B = np.clip(mu + sigma*np.random.randn(len(conn_A_B['i'])), W_MIN_INIT, W_MAX_INIT)
    initial_weights['A_B'] = np.copy(w_init_A_B)
    syn_MemA_to_PB = create_stdp_synapse(
        memory_module_A['E_chain'], column_B['P'], w_init_A_B,
        conn_data=conn_A_B, delay_model=delay_str,
        A_plus=0.02, A_minus=-0.03, taupre_ms=12.0, taupost_ms=24.0,
        multiplicative=True, name='stdp_AB'
    )
    synapse_map['A_B'] = syn_MemA_to_PB
    conn_B_A = create_deterministic_connections(N_E_MEM, N_EXC, conn_prob)
    w_init_B_A = np.clip(mu + sigma*np.random.randn(len(conn_B_A['i'])), W_MIN_INIT, W_MAX_INIT)
    initial_weights['B_A'] = np.copy(w_init_B_A)
    syn_MemB_to_PA = create_stdp_synapse(
        memory_module_B['E_chain'], column_A['P'], w_init_B_A,
        conn_data=conn_B_A, delay_model=delay_str,
        A_plus=0.02, A_minus=-0.03, taupre_ms=12.0, taupost_ms=24.0,
        multiplicative=True, name='stdp_BA'
    )
    synapse_map['B_A'] = syn_MemB_to_PA

    mon_weights_A_A = StateMonitor(syn_Mem_to_P_A, 'w', record=True, dt=100 * ms, name='mon_w_A_A')
    mon_weights_B_B = StateMonitor(syn_Mem_to_P_B, 'w', record=True, dt=100 * ms, name='mon_w_B_B')
    mon_weights_A_B = StateMonitor(syn_MemA_to_PB, 'w', record=True, dt=100 * ms, name='mon_w_A_B')
    mon_weights_B_A = StateMonitor(syn_MemB_to_PA, 'w', record=True, dt=100 * ms, name='mon_w_B_A')
    spikemon_input = SpikeMonitor(ThalamicInput, name='spikemon_input')

    # ##################################################################
    # ### YENİ EKLENEN "NaN KAPANI" ###
    # ##################################################################
    @network_operation(dt=1 * ms, name='instability_detector')
    def kararsizlik_dedektoru(t):
        # Kontrol edilecek tüm önemli nöron grupları
        groups_to_check = {
            'Kolon A - Tahmin (P)': column_A['P'],
            'Kolon A - Hata (PE)': column_A['PE'],
            'Kolon A - Inhibitör (I)': column_A['I'],
            'Kolon B - Tahmin (P)': column_B['P'],
            'Kolon B - Hata (PE)': column_B['PE'],
            'Kolon B - Inhibitör (I)': column_B['I'],
            'Bellek Modülü A': memory_module_A['E_chain'],
            'Bellek Modülü B': memory_module_B['E_chain']
        }

        for name, group in groups_to_check.items():
            # Grubun voltaj (v) değerlerinde NaN olup olmadığını kontrol et
            if np.any(np.isnan(group.v)):
                print("\n" + "=" * 80)
                print(f"!!! >>> KARARSIZLIK TESPİT EDİLDİ! SİMÜLASYON DURDURULUYOR. <<< !!!")
                print(f"\n--- KAZA RAPORU ---")
                print(f"Zaman: {t / ms:.2f} ms")
                print(f"Sorunlu Grup: '{name}'")

                # Hangi nöronların sorunlu olduğunu bul
                nan_indices = np.where(np.isnan(group.v))[0]
                print(f"Sorunlu Nöron İndeksleri: {nan_indices}")

                # İlk sorunlu nöronun detaylarını yazdır
                idx = nan_indices[0]
                print(f"\n--- Nöron #{idx} Detayları ---")
                print(f"  v = {group.v[idx]}")  # Voltaj
                if hasattr(group, 'u'):
                    print(f"  u = {group.u[idx]}")
                else:
                    print("  u: (yok)")

                # Eğer grupta akım değişkenleri varsa, onları da yazdır
                if hasattr(group, 'I_ampa'):
                    print(f"  I_ampa = {group.I_ampa[idx]}")
                if hasattr(group, 'I_nmda'):
                    print(f"  I_nmda = {group.I_nmda[idx]}")
                if hasattr(group, 'I_gaba'):
                    print(f"  I_gaba = {group.I_gaba[idx]}")

                print("=" * 80 + "\n")
                net.stop()  # Simülasyonu durdur
                return  # Diğer grupları kontrol etmeyi bırak

    # ##################################################################

    # Ağı toplama
    all_objects = [
        ThalamicInput, spikemon_input, thalamic_statemon,
        syn_Thalamic_PE_A, syn_Thalamic_PE_B,

        # --- EKLENDİĞİNDEN EMİN OLUN ---
        syn_P_to_Mem_A, syn_P_to_Mem_B,
        syn_Tone_to_Mem_A, syn_Tone_to_Mem_B,
        syn_Thal_to_Mem_A, syn_Thal_to_Mem_B,
        # -------------------------------

        syn_Mem_to_P_A, syn_Mem_to_P_B, syn_MemA_to_PB, syn_MemB_to_PA,
        mon_weights_A_A, mon_weights_B_B, mon_weights_A_B, mon_weights_B_A
    ]
    all_objects.extend(column_A.values())
    all_objects.extend(column_B.values())
    for obj in memory_module_A.values():
        if obj is not None:
            all_objects.append(obj)
    for obj in memory_module_B.values():
        if obj is not None:
            all_objects.append(obj)

    # tone_trig gruplarını da ekle
    all_objects.append(tone_trig_A)
    all_objects.append(tone_trig_B)

    # Kapanı da ağa ekliyoruz
    all_objects.append(kararsizlik_dedektoru)

    net = Network(all_objects)

    # ==================================================================
    # FPGA BAŞLANGIÇ AĞIRLIKLARI (INITIAL WEIGHTS EXPORT) - FIXED
    # ==================================================================
    print(f">>> FPGA İçin Ağırlık Matrisi Hazırlanıyor (Standalone Uyumlu)...")

    N_TOTAL_FPGA = 280
    fpga_matrix = np.zeros((N_TOTAL_FPGA, N_TOTAL_FPGA), dtype=int)
    SCALE = 65536

    # --- YARDIMCI 1: PLASTİK BAĞLANTILAR İÇİN (Elimizde Verisi Olanlar) ---
    def fill_from_data(conn_dict, weights_arr, src_offset, dst_offset):
        # Bu veriler Python'da zaten üretilmişti, o yüzden erişebiliriz.
        w_scaled = (weights_arr * SCALE).astype(int)
        for k in range(len(conn_dict['i'])):
            r = conn_dict['i'][k] + src_offset
            c = conn_dict['j'][k] + dst_offset
            if r < N_TOTAL_FPGA and c < N_TOTAL_FPGA:
                fpga_matrix[r, c] = w_scaled[k]

    # --- YARDIMCI 2: STATİK BAĞLANTILAR İÇİN (Matematiksel Üretim) ---
    def fill_static_block(src_start, src_count, dst_start, dst_count, weight_val):
        # Belirtilen aralıktaki nöronları "Hepsi-Hepsine" (All-to-All) bağlar.
        # FPGA'de sinyalin garantili gitmesi için p=1.0 (Full) yapıyoruz.
        w_int = int(weight_val * SCALE)

        for i in range(src_count):
            for j in range(dst_count):
                r = src_start + i
                c = dst_start + j
                fpga_matrix[r, c] = w_int

    def fill_static_one_to_one(src_start, dst_start, count, weight_val):
        # Birebir bağlantı (i -> i)
        w_int = int(weight_val * SCALE)
        for k in range(count):
            r = src_start + k
            c = dst_start + k
            fpga_matrix[r, c] = w_int

    # ---------------------------------------------------------
    # 1. PLASTİK BAĞLANTILAR (Değişken Ağırlıklı)
    # ---------------------------------------------------------
    fill_from_data(conn_A_A, initial_weights['A_A'], 80, 20)  # MemA -> PA
    fill_from_data(conn_B_B, initial_weights['B_B'], 180, 50)  # MemB -> PB
    fill_from_data(conn_A_B, initial_weights['A_B'], 80, 50)  # MemA -> PB
    fill_from_data(conn_B_A, initial_weights['B_A'], 180, 20)  # MemB -> PA

    # ---------------------------------------------------------
    # 2. STATİK BAĞLANTILAR (Sabit Ağırlıklı)
    # ---------------------------------------------------------
    # Ofsetler:
    # Thal:0, PA:20, PEA:30, IA:40, PB:50, PEB:60, IB:70

    # A) Thalamus -> PE (Giriş) - Ağırlık 50.0
    # Thal A (0-9) -> PE A (30-39)
    fill_static_block(src_start=0, src_count=10, dst_start=30, dst_count=10, weight_val=50.0)
    # Thal B (10-19) -> PE B (60-69)
    fill_static_block(src_start=10, src_count=10, dst_start=60, dst_count=10, weight_val=50.0)

    # B) Kolon A İçi (P, PE, I)
    # PE_A -> P_A (30 -> 20) : Ağırlık 10.0
    fill_static_block(30, 10, 20, 10, 10.0)

    # P_A -> I_A (20 -> 40) : Ağırlık 50.0
    fill_static_block(20, 10, 40, 10, 50.0)

    # I_A -> PE_A (40 -> 30) : Ağırlık -300.0 (Baskılayıcı)
    fill_static_block(40, 10, 30, 10, -300.0)

    # C) Kolon B İçi (P, PE, I)
    # PE_B -> P_B (60 -> 50)
    fill_static_block(60, 10, 50, 10, 10.0)

    # P_B -> I_B (50 -> 70)
    fill_static_block(50, 10, 70, 10, 50.0)

    # I_B -> PE_B (70 -> 60)
    fill_static_block(70, 10, 60, 10, -300.0)

    # ---------------------------------------------------------
    # 3. DOSYAYI KAYDET
    # ---------------------------------------------------------
    filename = "weights_init.mem"
    with open(filename, 'w') as f:
        for r in range(N_TOTAL_FPGA):
            for c in range(N_TOTAL_FPGA):
                val = fpga_matrix[r, c]
                val = val & 0xFFFFFFFF  # 32-bit Mask
                f.write(f"{val:08X}\n")

    print(f">>> TAM (Statik + Plastik) ağırlık dosyası '{filename}' başarıyla kaydedildi.")
    # ==================================================================


    print(f"\n>>> SİMÜLASYON BAŞLIYOR ({total_duration} sürecek)...")
    net.run(total_duration, report='text')

    print(">>> SİMÜLASYON TAMAMLANDI (veya NaN Kapanı ile durduruldu).")
    print("\n>>> Analiz ve Görselleştirme Aşaması...")

    # Analiz için monitörleri ve ağırlıkları toparla
    all_spike_monitors = {
        'Input Thalamic': spikemon_input,
        'Memory A (E_chain)': memory_module_A['spikemon_mem_e'],
        'Memory B (E_chain)': memory_module_B['spikemon_mem_e'],
        'Column A - PE': column_A['spikemon_pe'], 'Column A - P': column_A['spikemon_p'],
        'Column A - I': column_A['spikemon_i'],
        'Column B - PE': column_B['spikemon_pe'], 'Column B - P': column_B['spikemon_p'],
        'Column B - I': column_B['spikemon_i'],
    }
    final_weights = {
        'A_A': mon_weights_A_A.w[:, -1], 'B_B': mon_weights_B_B.w[:, -1],
        'A_B': mon_weights_A_B.w[:, -1], 'B_A': mon_weights_B_A.w[:, -1]
    }

    # Özetleri ve analizleri yazdır
    print_simulation_summary(all_spike_monitors, final_weights, N_input_per_tone)
    analyze_weight_changes(initial_weights['A_A'], final_weights['A_A'], col_id='A->A')
    analyze_weight_changes(initial_weights['B_B'], final_weights['B_B'], col_id='B->B')
    analyze_weight_changes(initial_weights['A_B'], final_weights['A_B'], col_id='A->B')
    analyze_weight_changes(initial_weights['B_A'], final_weights['B_A'], col_id='B->A')

    # Grafikleri çizdir
    weight_stats = {
        'A_A': {'t': mon_weights_A_A.t / ms, 'mean': np.mean(mon_weights_A_A.w, axis=0),
                'min': np.min(mon_weights_A_A.w, axis=0), 'max': np.max(mon_weights_A_A.w, axis=0)},
        'B_B': {'t': mon_weights_B_B.t / ms, 'mean': np.mean(mon_weights_B_B.w, axis=0),
                'min': np.min(mon_weights_B_B.w, axis=0), 'max': np.max(mon_weights_B_B.w, axis=0)},
        'A_B': {'t': mon_weights_A_B.t / ms, 'mean': np.mean(mon_weights_A_B.w, axis=0),
                'min': np.min(mon_weights_A_B.w, axis=0), 'max': np.max(mon_weights_A_B.w, axis=0)},
        'B_A': {'t': mon_weights_B_A.t / ms, 'mean': np.mean(mon_weights_B_A.w, axis=0),
                'min': np.min(mon_weights_B_A.w, axis=0), 'max': np.max(mon_weights_B_A.w, axis=0)},
    }
    plot_weight_statistics(weight_stats)

    print(">>> Sonuç grafikleri oluşturuluyor...", flush=True)
    # plot_memory_activity(memory_module_A['spikemon_mem_e'], memory_module_B['spikemon_mem_e'])
    # plot_weight_heatmap(synapse_map['A_A'], initial_weights['A_A'], 'A -> A', N_E_MEM, N_EXC)
    # plot_weight_heatmap(synapse_map['B_B'], initial_weights['B_B'], 'B -> B', N_E_MEM, N_EXC)
    # plot_weight_heatmap(synapse_map['A_B'], initial_weights['A_B'], 'A -> B', N_E_MEM, N_EXC)
    # plot_weight_heatmap(synapse_map['B_A'], initial_weights['B_A'], 'B -> A', N_E_MEM, N_EXC)

    # plot_weight_distribution(list(synapse_map.values()), list(synapse_map.keys()), synapse_map['A_A'].w_max[0])

    plot_example_synapses(mon_weights_A_A, synapse_map['A_A'], initial_weights['A_A'], final_weights['A_A'], 'Bağlantı [A -> A]', 'royalblue')
    plot_example_synapses(mon_weights_B_B, synapse_map['B_B'], initial_weights['B_B'], final_weights['B_B'], 'Bağlantı [B -> B]', 'crimson')
    plot_example_synapses(mon_weights_A_B, synapse_map['A_B'], initial_weights['A_B'], final_weights['A_B'], 'Bağlantı [A -> B]', 'mediumseagreen')
    plot_example_synapses(mon_weights_B_A, synapse_map['B_A'], initial_weights['B_A'], final_weights['B_A'], 'Bağlantı [B -> A]', 'darkorange')

    mask_A = spikemon_input.i < N_input_per_tone
    t_thalamic_A, i_thalamic_A = spikemon_input.t[mask_A], spikemon_input.i[mask_A]
    mask_B = spikemon_input.i >= N_input_per_tone
    t_thalamic_B, i_thalamic_B = spikemon_input.t[mask_B], spikemon_input.i[mask_B] - N_input_per_tone
    thalamic_inputs = {'A': (t_thalamic_A, i_thalamic_A), 'B': (t_thalamic_B, i_thalamic_B)}
    # for col_id, col_data, mem_mon, col_color in [('A', column_A, memory_module_A, 'royalblue'), ('B', column_B, memory_module_B, 'crimson')]:
    # fig = plt.figure(figsize=(22, 12)); fig.suptitle(f"Kolon {col_id} Aktivitesi ({paradigm_name} Senaryosu)", fontsize=18, color=col_color)
    # main_grid = fig.add_gridspec(1, 3, wspace=0.3)
    # plot_layer_activity(fig, main_grid[0, 0], (col_data.get('statemon_pe'), col_data['spikemon_pe'], col_data['ratemon_pe']), title_prefix="Prediction Error Aktivitesi", input_data=thalamic_inputs[col_id], input_title="Thalamic Girdi")
    # plot_layer_activity(fig, main_grid[0, 1], (col_data.get('statemon_p'), col_data['spikemon_p'], col_data['ratemon_p']), title_prefix="Predictive Aktivitesi", input_data=mem_mon['spikemon_mem_e'], input_title="Bellek Girdi")
    # plot_layer_activity(fig, main_grid[0, 2], (col_data.get('statemon_i'), col_data['spikemon_i'], col_data['ratemon_i']), title_prefix="Inhibitory Aktivitesi")

    # Paradigmaya özel analiz ve çizim
    if paradigm_name == 'omission':
        plot_omission_response_comparison(column_A, spikemon_input, thalamic_statemon,
                                          memory_module_A, tones, times,
                                          paradigm_params, N_input_per_tone,
                                          window_start_ms=4000, window_end_ms=4500)
        analyze_omission_response(column_A['spikemon_pe'], tones, times, paradigm_params,
                                  window_start_ms=4000, window_end_ms=4500)
    else:
        # create_mmn_comparison_plot(tones, times, column_A, column_B,
        #                            spikemon_input, thalamic_statemon,
        #                            memory_module_A, memory_module_B,
        #                            N_input_per_tone, window_start_ms=398000, window_end_ms=400000)

        create_mmn_comparison_plot_short(tones, times, column_A, column_B,
                                         spikemon_input, thalamic_statemon,
                                         memory_module_A, memory_module_B,
                                         N_input_per_tone, window_start_ms=-50, window_end_ms=250, exclude_first=200)

        print(">>> İnteraktif gezgin hazırlanıyor. Lütfen grafik penceresini bekleyin...")
        all_interactive_widgets['explorer'] = create_interactive_explorer(
            total_duration=total_duration,
            monitors_A=column_A,
            monitors_B=column_B,
            thalamic_spikemon=spikemon_input,
            N_input_per_tone=N_input_per_tone,
            memory_module_A=memory_module_A,
            memory_module_B=memory_module_B,
            model_params=model_params,
            window_width_ms=300
        )

        all_interactive_widgets['weights'] = create_weight_profile_figure(
            total_duration=total_duration,
            model_params=model_params,
            syn_AA=syn_Mem_to_P_A,  # A→A
            syn_AB=syn_MemA_to_PB,  # A→B
            syn_BB=syn_Mem_to_P_B,  # B→B
            syn_BA=syn_MemB_to_PA,  # B→A
            wmon_AA=mon_weights_A_A,  # varsa
            wmon_AB=mon_weights_A_B,
            wmon_BB=mon_weights_B_B,
            wmon_BA=mon_weights_A_B,  # Orijinal kodda hata vardı, BA olmalı
            t_init_ms=0.0
        )
        # print_mmn_summary(
        #     tones, times,
        #     column_A, column_B,
        #     layers=('pe', 'p'),
        #     window_ms=(0, 150),  # 0..150 veya 0..250 ms
        #     baseline_ms=(-50, 0),  # istersen None
        #     exclude_first=200,
        #     n_trials=100
        # )
        plot_AB_sequence_window(
            tones, times,
            monitors_A=column_A, monitors_B=column_B,
            thalamic_spikemon=spikemon_input, thalamic_statemon=thalamic_statemon,
            N_input_per_tone=N_input_per_tone,
            pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50,
            t_min_ms=350000,  # öğrenme oturduktan sonra örnek seç
            prefer='last'  # son uygun AB çifti
        )
        SOA_eff = paradigm_params.get('soa', None) or paradigm_params.get('intra_isi', None)

        # Eğer parametrelerden gelmediyse, times vektöründen türet (medyan fark)
        if SOA_eff is None:
            if len(times) > 1:
                # units korumak için ms'e bölüp medyan al, sonra tekrar ms ile çarp
                dt_ms = np.diff(times) / ms
                SOA_eff = np.median(dt_ms) * ms
            else:
                SOA_eff = 50 * ms  # güvenli varsayılan (gerekirse değiştir)

        # Kodun geri kalanıyla uyum için aynı ismi kullan:
        SOA = SOA_eff
        if SOA is not None:
            for memE in (memory_module_A['E_chain'], memory_module_B['E_chain']):
                # SOA 200ms ise 160ms dinlensin.
                # Geriye kalan 40ms'de "tone_gate" kapalı olacağı için P ateşlese bile sorun olmaz.
                # Sadece yeni ses geldiğinde kapı açılır ve zincir başlar.
                memE.ref_time[0] = max(1 * ms, 0.8 * SOA)
        # Eğer tam bellek modülü (E_chain + I_pool) kullanıyorsan:
        chain_delay = model_params['mem_all']['weights']['CHAIN_DELAY']

        # Eğer "simple LIF chain" kullanıyorsan:
        # chain_delay = SIMPLE_MEM_PARAMS.get('d_ff', 1.5*ms)

        # Thalamus spike monitörü: senin dosyanda 'spikemon_input' olarak geçiyor
        # Memory spike monitörleri:
        spk_mem_A = memory_module_A['spikemon_mem_e']
        spk_mem_B = memory_module_B['spikemon_mem_e']

        # A ve B için alt alta thalamic vs memory grafikleri:
        summary_A, rows_A = plot_input_vs_memory('A', spikemon_input, N_input_per_tone,
                                                 spk_mem_A, tones, times, SOA, chain_delay)
        report_missed(rows_A)

        summary_B, rows_B = plot_input_vs_memory('B', spikemon_input, N_input_per_tone,
                                                 spk_mem_B, tones, times, SOA, chain_delay)
        report_missed(rows_B)

        # plot_figure2_classic(
        #     tones=tones, times=times,
        #     monitors_A=column_A, monitors_B=column_B,
        #     thalamic_spikemon=spikemon_input,  # senin dosyada bu isimle
        #     N_input_per_tone=N_input_per_tone,
        #     window_ms=(-50, 250), bin_ms=2, stim_ms=50, gap_ms=200,
        #     title="Classic oddball – Figure 2"
        # )

        # plot_figure2_classic_paperlike(
        #     tones=tones, times=times,
        #     monitors_A=column_A, monitors_B=column_B,
        #     thalamic_spikemon=spikemon_input,
        #     N_input_per_tone=N_input_per_tone,
        #     window_ms=(-50, 250), bin_ms=2, stim_ms=50,
        #     title="Classic oddball – Figure 2 (paper-like)"
        # )

        # print(">>> plot_AB_sequence_average ÇAĞRILIYOR (kaynak:", __file__, ")")
        #
        # plot_AB_sequence_average(
        #     tones, times,
        #     monitors_A=column_A, monitors_B=column_B,
        #     thalamic_spikemon=spikemon_input,
        #     N_input_per_tone=N_input_per_tone,
        #     pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50,
        #     t_min_ms=350000, gap_tol_ms=30,  # 200±30 ms kabul
        #     bin_ms=2, smooth_ms=8, rate_per_neuron=False
        # )

        # plot_AB_sequence_average(
        #     tones, times,
        #     monitors_A=column_A, monitors_B=column_B,
        #     thalamic_spikemon=spikemon_input,
        #     N_input_per_tone=N_input_per_tone,
        #     pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50,
        #     t_min_ms = 0,t_max_ms = 50000, gap_tol_ms=30,  # 200±30 ms kabul
        #     bin_ms=2, smooth_ms=8, rate_per_neuron=False
        # )

        # # Standart (A) koşulu için
        # plot_I_syn_multi(column_A['statemon_pe'], layer_name="PE Layer (A)", n_neurons=10)
        # plot_I_syn_multi(column_A['statemon_p'], layer_name="P Layer (A)", n_neurons=10)
        #
        # # Aykırı (B) koşulu için
        # plot_I_syn_multi(column_B['statemon_pe'], layer_name="PE Layer (B)", n_neurons=10)
        # plot_I_syn_multi(column_B['statemon_p'], layer_name="P Layer B)", n_neurons=10)

        # Yeni hali
        # quantify_mmn_response(column_A['spikemon_pe'], column_B['spikemon_pe'], tones, times,
        #                       window_start_ms=398000, window_end_ms=400000)

        # plot_thalamic_input_only(spikemon_input, total_duration, N_input_per_tone,
        #                         start_ms=398000, end_ms=400000)

        print("#" * 70 + "\n")

    #def count_thalamic_in_window(spmon, tones, times, N, stim_dur):
    #     A = B = 0
    #     for t, tone in zip(times, tones):
    #         m = (spmon.t >= t) & (spmon.t < t + stim_dur)
    #         if tone == 0:  # A
    #             A += np.sum(m & (spmon.i < N))
    #         else:  # B
    #             B += np.sum(m & (spmon.i >= N))
    #     return A, B

    # A_in, B_in = count_thalamic_in_window(spikemon_input, tones, times, N_input_per_tone, STIMULUS_DURATION)
    # print(f"[Uyaran penceresi] Thalamic A: {A_in}, B: {B_in}")

    # A_times = [times[i] for i in np.where(tones == 0)[0]]
    # B_times = [times[i] for i in np.where(tones == 1)[0]]
    #
    # # Bellek A zinciri için "başlatma başarı oranı"
    # mem_start_success_ratio(memory_module_A['spikemon_mem_e'], A_times, memory_module_B['spikemon_mem_e'], B_times,
    #                         t_min=350000 * ms, within=15 * ms)

    # ... run_single_simulation(...) gövdesinin SONUNDAKİ return satırından hemen önce:

    # ---- GÜNCELLENMİŞ VE DOĞRU SONUÇ PAKETİ ----
    def _safe_mon(mon):
        # Monitör None olabilir; olduğu gibi döndür
        return mon if mon is not None else None

    result_package = {
        "tones": tones,
        "times": times,
        "total_duration": total_duration,  # İnteraktif gezgin için bu bilgiyi de ekleyelim

        "monitors_A": {
            "spikemon_p": _safe_mon(column_A.get('spikemon_p')),
            "spikemon_pe": _safe_mon(column_A.get('spikemon_pe')),
            "statemon_p": _safe_mon(column_A.get('statemon_p')),
            "statemon_pe": _safe_mon(column_A.get('statemon_pe')),
        },
        "monitors_B": {
            "spikemon_p": _safe_mon(column_B.get('spikemon_p')),
            "spikemon_pe": _safe_mon(column_B.get('spikemon_pe')),
            "statemon_p": _safe_mon(column_B.get('statemon_p')),
            "statemon_pe": _safe_mon(column_B.get('statemon_pe')),
        },
        "memory_module_A": {
            "spikemon_mem_e": _safe_mon(memory_module_A.get('spikemon_mem_e')),
        },
        "memory_module_B": {
            "spikemon_mem_e": _safe_mon(memory_module_B.get('spikemon_mem_e')),
        },
        "thalamic_spikemon": _safe_mon(spikemon_input),
        "N_input_per_tone": N_input_per_tone,

        # Ağırlık verileri zaten doğru okunuyordu, olduğu gibi kalabilir
        "final_weights": final_weights
    }
    return result_package, all_interactive_widgets





def _first_AB_pair(tones, times, t_min_ms=0, gap_target_ms=200, gap_tol_ms=10):
    tones = np.asarray(tones)
    idx = np.where((tones[:-1] == 0) & (tones[1:] == 1))[0]
    if len(idx) == 0:
        return None, None
    # gap filtrele (opsiyonel)
    tA = np.array([float(times[i] / ms) for i in idx])
    tB = np.array([float(times[i + 1] / ms) for i in idx])
    m = (tA >= t_min_ms) & (np.abs((tB - tA) - gap_target_ms) <= gap_tol_ms)
    if not np.any(m):
        i = idx[0]
    else:
        i = idx[m][0]
    return times[i], times[i + 1]


def _count_spikes_in_window(spikemon, t0, start_ms=0, end_ms=150):
    if spikemon is None:
        return 0
    t_start = t0 + start_ms * ms
    t_end = t0 + end_ms * ms
    m = (spikemon.t >= t_start) & (spikemon.t < t_end)
    return int(np.sum(m))


def _psth(spikemon, t_ref, pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50, bin_ms=2):
    if spikemon is None:
        return np.zeros(1), np.zeros(1)
    # A’ya göre hizalanmış zaman
    t0_abs = t_ref - pre_ms * ms
    t1_abs = t_ref + (pre_ms + stim_ms + gap_ms + stim_ms + post_ms) * ms
    m = (spikemon.t >= t0_abs) & (spikemon.t < t1_abs)
    t_rel_ms = (spikemon.t[m] - t_ref) / ms  # ms cinsinden, A olayı referans
    # binleme
    grid = np.arange(-pre_ms, pre_ms + stim_ms + gap_ms + stim_ms + post_ms + bin_ms, bin_ms, dtype=float)
    hist, _ = np.histogram(t_rel_ms, bins=grid)
    # Hz/nöron yerine sade spike/bin veriyoruz; istersen / (bin_ms/1000) / N ile ölçekleyebilirsin
    centers = 0.5 * (grid[:-1] + grid[1:])
    return centers, hist.astype(float)


def summarize_single_run(package):
    tones = package["tones"];
    times = package["times"]
    monA = package["monitors_A"];
    monB = package["monitors_B"]
    th = package["thalamic_spikemon"]
    N_in = package["N_input_per_tone"]

    # AB çifti (A sonra B)
    tA, tB = _first_AB_pair(tones, times, t_min_ms=0)
    if tA is None:
        return {
            "scalars": {"PE_A_0_150": np.nan, "PE_B_0_150": np.nan},
            "traces": {}
        }

    # 0–150ms penceresinde PE_A/PE_B spike sayıları
    peA = monA.get("spikemon_pe");
    peB = monB.get("spikemon_pe")
    sA = _count_spikes_in_window(peA, tA, 0, 150)
    sB = _count_spikes_in_window(peB, tB, 0, 150)

    # PSTH (hizalı)
    gridA, psthA = _psth(peA, tA, pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50, bin_ms=2)
    gridB, psthB = _psth(peB, tA, pre_ms=50, stim_ms=50, gap_ms=200, post_ms=50, bin_ms=2)  # aynı grid’e oturtuyoruz

    # Güvenlik: gridler eşit değilse yeniden örnekleme yapılabilir; basitçe eşit olduklarını varsayıyoruz
    if gridA.shape != gridB.shape or not np.allclose(gridA, gridB):
        # en basit çözüm: kısa olanı kırp
        L = min(len(gridA), len(gridB))
        grid = gridA[:L]
        psthA = psthA[:L];
        psthB = psthB[:L]
    else:
        grid = gridA

    return {
        "scalars": {"PE_A_0_150": float(sA), "PE_B_0_150": float(sB)},
        "traces": {"psth_grid_ms": grid, "psth_PE_A": psthA, "psth_PE_B": psthB}
    }


def _combine_averages(summaries):
    """Birden çok özetin ortalamasını alır."""
    # Skalerler
    keys_scalar = summaries[0]["scalars"].keys()
    avg_scalars = {k: float(np.nanmean([s["scalars"][k] for s in summaries])) for k in keys_scalar}

    # İzler: aynı grid varsayımı
    grid = summaries[0]["traces"]["psth_grid_ms"]
    A_stack = np.vstack([s["traces"]["psth_PE_A"] for s in summaries])
    B_stack = np.vstack([s["traces"]["psth_PE_B"] for s in summaries])
    avg_traces = {
        "psth_grid_ms": grid,
        "psth_PE_A_mean": np.nanmean(A_stack, axis=0),
        "psth_PE_B_mean": np.nanmean(B_stack, axis=0),
        "psth_PE_A_std": np.nanstd(A_stack, axis=0),
        "psth_PE_B_std": np.nanstd(B_stack, axis=0),
    }
    return {"scalars": avg_scalars, "traces": avg_traces}





def mem_start_success_ratio(spikemon_mem_A_e,
                            A_times,
                            spikemon_mem_B_e,  # <-- yeni: B memory spike monitor
                            B_times,  # <-- yeni: B olay zamanları
                            idxA0=0,  # A zinciri ilk nöron
                            idxB0=0,  # B zinciri ilk nöron (None -> auto)
                            t_min=350000 * ms,
                            within=10 * ms):
    """
    A ve (opsiyonel) B bellek modüllerinde zincir başlatma başarısı.
    'within' penceresinde ilk nöron spike atarsa 'başladı' sayılır.
    """
    import numpy as np
    from brian2 import ms

    def _filter_after(ts):  # Quantity list
        return [t for t in ts if t >= t_min]

    def _count_starts(spmon, idx0, event_times):
        s_times = spmon.t[spmon.i == idx0]
        cnt = 0
        for t0 in event_times:
            if np.any((s_times >= t0) & (s_times < t0 + within)):
                cnt += 1
        return cnt, len(event_times)

    def _auto_detect_start_index(spmon, event_times):
        uniq = np.unique(spmon.i)
        if uniq.size == 0:
            return 0
        best_idx, best_hits = int(uniq[0]), -1
        for i in uniq:
            hits, _ = _count_starts(spmon, int(i), event_times)
            if hits > best_hits:
                best_idx, best_hits = int(i), hits
        return best_idx

    # --- A ölçümü ---
    A_times_f = _filter_after(A_times)
    A_hits, A_total = _count_starts(spikemon_mem_A_e, idxA0, A_times_f)
    A_ratio = (A_hits / A_total) if A_total else 0.0
    print(f"[Bellek Başlatma|A] idx0={idxA0}  t>{int(t_min / ms)}ms  A={A_total}, "
          f"başlayan={A_hits}, oran={A_ratio:.2f}")

    result = {"A": {"idx0": idxA0, "total": A_total, "started": A_hits, "ratio": A_ratio}}

    # --- B ölçümü (varsa) ---
    if B_times is not None:
        if spikemon_mem_B_e is None:
            raise ValueError("B ölçümü için 'spikemon_mem_B_e' verilmelidir.")
        B_times_f = _filter_after(B_times)
        if idxB0 is None:
            idxB0 = _auto_detect_start_index(spikemon_mem_B_e, B_times_f)
            print(f"[Bellek Başlatma|B] idx0 otomatik bulundu: {idxB0}")
        B_hits, B_total = _count_starts(spikemon_mem_B_e, idxB0, B_times_f)
        B_ratio = (B_hits / B_total) if B_total else 0.0
        print(f"[Bellek Başlatma|B] idx0={idxB0}  t>{int(t_min / ms)}ms  B={B_total}, "
              f"başlayan={B_hits}, oran={B_ratio:.2f}")
        result["B"] = {"idx0": idxB0, "total": B_total, "started": B_hits, "ratio": B_ratio}

    return result


def export_weights_for_fpga(syn_list, total_neurons, filename="weights_matrix_full.mem"):
    print(f">>> FPGA İçin Ağırlık Matrisi Oluşturuluyor: {filename}")

    # 280x280'lik boş bir matris (0 ile dolu)
    # Değerler Q16.16 formatında (Integer) olacak
    matrix = np.zeros((total_neurons, total_neurons), dtype=int)

    SCALE = 65536

    # Sıralama (Mapping):
    # 0-19: Thalamus
    # 20-29: PA, 30-39: PEA, 40-49: IA
    # 50-59: PB, 60-69: PEB, 70-79: IB
    # 80-179: MemA
    # 180-279: MemB

    # Helper: Brian2 objesinden matris indeksine çevir
    # (Burada her nöron grubu için offset'i bilmemiz lazım, bu kısmı manuel ayarlamak gerekebilir)
    # Örnek olarak syn_Mem_to_P_A'yı alalım:
    # Kaynak: MemA (Offset 80), Hedef: PA (Offset 20)

    # Tüm sinaps objelerini gez (syn_list içinde hepsi olmalı)
    for syn in syn_list:
        # Not: Brian2'de syn.i ve syn.j, o grubun içindeki lokal indekstir.
        # Bunlara global offset eklemeliyiz.

        # Bu kısım biraz manuel mapping gerektirir.
        # Örneğin:
        src_offset = 0
        dst_offset = 0

        if "E_chain_Mem_A" in syn.source.name:
            src_offset = 80
        elif "Thalamic" in syn.source.name:
            src_offset = 0
        # ... diğerleri ...

        if "P_A" in syn.target.name: dst_offset = 20
        # ... diğerleri ...

        # Matrise yaz
        weights_scaled = (syn.w * SCALE).astype(int)
        for k in range(len(syn.i)):
            global_src = syn.i[k] + src_offset
            global_dst = syn.j[k] + dst_offset
            if global_src < total_neurons and global_dst < total_neurons:
                matrix[global_src, global_dst] = weights_scaled[k]

    # Dosyaya Yaz (Hex Formatında)
    with open(filename, 'w') as f:
        for r in range(total_neurons):
            for c in range(total_neurons):
                # 32-bit Hex (8 karakter)
                val = matrix[r, c]
                f.write(f"{val:08X}\n")  # Yan yana değil alt alta yazmak BRAM için daha güvenli

    print(">>> .mem dosyası hazır!")


# ======================================================================
# BÖLÜM 3: ANA ÇALIŞTIRMA BLOGU
# ======================================================================

if __name__ == '__main__':
    # Model parametreleri aynı kalıyor.
    model_params = {
        'N_EXC': 10, 'N_INH': 10, 'N_E_MEM': 100, 'N_I_MEM': 25,

        # --- YENİ LIF PARAMETRELERİ (Kortikal Kolonlar İçin) ---
        'exc': {
            'v_rest': -65 * mV,
            'v_reset': -65 * mV,
            'v_threshold': -60 * mV,  # Eşik değer (ayarlamak gerekebilir)
            'tau_m': 20 * ms,         # Membran zaman sabiti
            'V_E': 0 * mV, 'V_I': -80 * mV,
            'g_ampa': 0.075, 'g_gaba': 0.0075, 'g_nmda': 0.002,
            'tau_ampa': 2 * ms, 'tau_gaba': 10 * ms,
            'tau_nmda_rise': 2 * ms, 'tau_nmda_decay': 100 * ms,
            'alpha_nmda': 0.5 / ms, 'Mg2_conc': 0.001
        },
        'inh': {
            'v_rest': -60 * mV,
            'v_reset': -60 * mV,
            'v_threshold': -55 * mV,  # Inhibitörler biraz daha kolay ateşlesin
            'tau_m': 10 * ms,         # Daha hızlı tepki versin
            'V_E': 0 * mV,
            'V_I': -80 * mV,  # GABA reversal potansiyeli
            'g_gaba': 0.0075,  # GABA iletkenliği
            'tau_gaba': 10 * ms,  # GABA zaman sabiti
            'g_ampa': 0.075, 'g_nmda': 0.002,
            'tau_ampa': 2 * ms,
            'tau_nmda_rise': 2 * ms, 'tau_nmda_decay': 100 * ms,
            'alpha_nmda': 0.5 / ms, 'Mg2_conc': 0.001
        },
        'input': {
            'v_rest': -65 * mV,
            'v_reset': -65 * mV,
            'v_threshold': -60 * mV,  # Input zor ateşlesin (biz akımla zorlayacağız)
            'tau_m': 20 * ms
        },
        'syn_weights': {
            # w_EE: 50.0 kalsın, ama varyansı (random kısmı) biraz kısalım ki
            # bazı nöronlar aşırı güçlü olup sistemi domine etmesin.
            "w_EE": 'clip(50.0 + sqrt(0.1 * 50.0) * randn(), 0, 150.0)',

            # w_EI: 50.0 iyi, P nöronları I'yı güzel uyarıyor.
            "w_EI": 'clip(50.0 + sqrt(0.1 * 50.0) * randn(), 0, 200.0)',

            # DEĞİŞİKLİK BURADA: w_IE (Baskılama)
            # 150'den 300'e çıkarıyoruz. Tahmin (P), Hatayı (PE) ezmeli.
            "w_IE": 'clip(300.0 + sqrt(0.1 * 300.0) * randn(), 0, 600.0)'
        },
        'mem_all': {
            'exc': {'a': 0.02, 'b': '0.2 + 0.04*rand()**2', 'c': '(-65 + 10*rand()**2)*mV',
                    'd': '(15 - 3*rand()**2)*mV', 'V_E': 40 * mV, 'V_I': -80 * mV, 'g_ampa': 0.0075, 'g_gaba': 0.0075,
                    'tau_ampa': 1.25 * ms, 'tau_gaba': 14 * ms, 'g_nmda': 0.0001, 'tau_nmda_rise': 2 * ms,
                    'tau_nmda_decay': 80 * ms, 'alpha_nmda': 0.15 / ms, 'Mg2_conc': 0.001, 'sigma_noise': 0},
            'inh': {'a': '0.06 + 0.04*rand()**2', 'b': 0.2, 'c': -60 * mV, 'd': 10 * mV, 'V_E': 40 * mV,
                    'g_ampa': 0.0075, 'tau_ampa': 2 * ms, 'g_nmda': 0.0025, 'tau_nmda_rise': 4 * ms,
                    'tau_nmda_decay': 40 * ms, 'alpha_nmda': 0.15 / ms, 'Mg2_conc': 0.01, 'sigma_noise': 0},
            'weights': {"w_EE_mem": 140, "w_IE_mem": 0.5, "w_EI_mem": 40, "p_IE": 0.30, "p_EI": 0.2,
                        "CHAIN_DELAY": 1 * ms, "E_TO_I_DELAY": 0.5 * ms, "I_TO_E_DELAY": 0.5 * ms}
        }
    }

    # --- DENEY SENARYOLARI (BİRLEŞTİRİLMİŞ) ---
    classic_params = {'total_tones': 200, 'deviant_prob': 0.1, 'soa': 200 * ms, 'min_deviant_ms': 10000*ms}
    alternating_params = {'total_tones': 300, 'deviant_prob': 0.15, 'soa': 200 * ms, 'min_deviant_ms': 30000*ms}
    local_global_params = {'num_sequences': 100, 'intra_isi': 150 * ms, 'inter_soa': 1200 * ms,
                           'probabilities': [0.7, 0.2, 0.1]}
    omission_params = {'num_pairs': 1500, 'omission_prob': 0.10, 'isi': 200 * ms}

    # --- HANGİ DENEYİ ÇALIŞTIRACAĞINI SEÇ ---
    experiment_to_run = 'classic'

    if experiment_to_run == 'classic':
        results, interactive_widgets_main = run_single_simulation(paradigm_name='classic', paradigm_params=classic_params,
                              model_params=model_params, stimulus_amplitude=120, seed_value=42)
    elif experiment_to_run == 'alternating':
        results, interactive_widgets_main = run_single_simulation(paradigm_name='alternating', paradigm_params=alternating_params,
                              model_params=model_params, stimulus_amplitude=3.0, seed_value=42)
    elif experiment_to_run == 'local_global':
        results, interactive_widgets_main = run_single_simulation(paradigm_name='local_global', paradigm_params=local_global_params,
                              model_params=model_params, stimulus_amplitude=3.0, seed_value=42)
    elif experiment_to_run == 'omission':
        results, interactive_widgets_main = run_single_simulation(paradigm_name='omission', paradigm_params=omission_params,
                              model_params=model_params, stimulus_amplitude=1.9, seed_value=42)

    outdir = os.path.join("fig_out", time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(outdir, exist_ok=True)

    for i, num in enumerate(plt.get_fignums(), start=1):
        fig = plt.figure(num)
        fig.savefig(os.path.join(outdir, f"fig_{i:02d}.png"), dpi=200, bbox_inches='tight')

    print("Tüm figürler kaydedildi. Dizin:", outdir)




    # ==================================================================
    # FPGA FIXED-POINT ANALİZİ (SANITY CHECK)
    # ==================================================================
    print("\n" + "=" * 60)
    print(">>> FPGA FIXED-POINT ANALİZİ BAŞLIYOR...")
    print("=" * 60)

    # 1. Ölçekleme Faktörü (2^10 = 1024)
    # Bit kaydırma miktarı: 10 bit
    SCALE_BITS = 16  # 10 yerine 12 (4096) deneyelim, hassasiyet artsın
    SCALE = 2 ** SCALE_BITS
    print(f"Seçilen Ölçekleme: 2^{SCALE_BITS} = {SCALE}")

    # 2. Voltaj Kontrolü (Taşma var mı?)
    # Voltajlar genelde -80mV ile +50mV arasındadır.
    v_min_float = -0.080  # -80 mV (Brian2'de volt bazlıdır)
    v_max_float = 0.050  # +50 mV

    v_min_int = int(v_min_float * SCALE * 1000)  # mV'ye çevirip ölçekliyoruz
    v_max_int = int(v_max_float * SCALE * 1000)

    print(f"\n--- Voltaj Aralığı (Register Boyutu) ---")
    print(f"Min Voltaj (-80mV): {v_min_int}")
    print(f"Max Voltaj (+50mV): {v_max_int}")

    if v_min_int < -32768 or v_max_int > 32767:
        print("UYARI: Değerler 16-bit integer (-32768 ... 32767) sınırını aşıyor!")
        print("ÇÖZÜM: 32-bit register kullanmamız gerekecek.")
    else:
        print("DURUM: 16-bit register (signed) yeterli görünüyor.")

    # 3. Zaman Sabiti Kontrolü (Sıfıra düşme riski!)
    # Formül: decay_factor = dt / tau
    dt_val = 0.05  # ms
    tau_exc = 20.0  # ms

    decay_float = dt_val / tau_exc
    decay_int = int(decay_float * SCALE)

    print(f"\n--- Zaman Sabiti ve Sönümleme (Decay) ---")
    print(f"Simülasyon dt: {dt_val} ms")
    print(f"Nöron tau: {tau_exc} ms")
    print(f"Float Decay (dt/tau): {decay_float:.6f}")
    print(f"Fixed-Point Decay: {decay_int}")

    if decay_int == 0:
        print("\n!!! KRİTİK HATA: Decay faktörü 0 oldu! !!!")
        print("Nöronlar sızıntı yapamaz (sonsuza kadar şarjlı kalır).")
        print("ÇÖZÜM: SCALE_BITS'i artırmalıyız (örn: 12, 14, 16).")
    elif decay_int < 10:
        print("\nUYARI: Decay faktörü çok küçük (<10). Yuvarlama hataları oluşabilir.")
    else:
        print("DURUM: Decay faktörü güvenli aralıkta.")

    # 4. Ağırlık Kontrolü
    # Ağırlıklar (w) yaklaşık 50.0 ile 300.0 arasında.
    w_example = 50.0
    w_int = int(w_example * SCALE)  # Dikkat: Ağırlık zaten boyutsuzsa direkt çarpılır
    # Ama senin kodunda w, voltaj etkisi yaratıyor. Eğer w=50 demek 50mV demekse:
    # O zaman w_int hesabı voltaj gibi olmalı.
    # Ancak senin modelinde w doğrudan "v += w" yapıyor (Instant Jump için).
    # LIF modelinde ise "I = g * w * (E-v)"

    print(f"\n--- Ağırlık Hassasiyeti ---")
    print(f"Örnek Ağırlık (w=50.0): {int(w_example)}")
    # Not: FPGA'da ağırlıkları da ölçekleyeceğiz.

    print("=" * 60 + "\n")

    plt.show()











