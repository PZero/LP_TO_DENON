import math
import struct
import wave
import os
import sys

def generate_sine_wave(frequency, duration, volume=0.3, sample_rate=44100):
    num_samples = int(duration * sample_rate)
    data = bytearray()
    # Apply fade-in and fade-out to avoid clicks
    fade_len = int(0.05 * sample_rate)  # 50ms fade
    for i in range(num_samples):
        envelope = 1.0
        if i < fade_len:
            envelope = i / fade_len
        elif i > num_samples - fade_len:
            envelope = (num_samples - i) / fade_len
            
        sample = volume * envelope * math.sin(2 * math.pi * frequency * i / sample_rate)
        val = int(sample * 32767)
        data.extend(struct.pack('<h', val))
    return data

def save_wav(filename, data, sample_rate=44100):
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(data)
    print(f"Generated {filename}")

def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "./sounds"
    
    # 1. Boot chime: Due note ascendenti rapide (C5 -> G5)
    boot_data = bytearray()
    boot_data.extend(generate_sine_wave(523.25, 0.15)) # C5
    boot_data.extend(generate_sine_wave(783.99, 0.35)) # G5
    save_wav(os.path.join(target_dir, "boot.wav"), boot_data)
    
    # 2. Connected chime: Triade maggiore ascendente (C5 -> E5 -> G5 -> C6)
    conn_data = bytearray()
    conn_data.extend(generate_sine_wave(523.25, 0.12)) # C5
    conn_data.extend(generate_sine_wave(659.25, 0.12)) # E5
    conn_data.extend(generate_sine_wave(783.99, 0.12)) # G5
    conn_data.extend(generate_sine_wave(1046.50, 0.30)) # C6
    save_wav(os.path.join(target_dir, "connected.wav"), conn_data)
    
    # 3. Disconnected chime: Triade discendente malinconica (G5 -> E5 -> C5)
    disconn_data = bytearray()
    disconn_data.extend(generate_sine_wave(783.99, 0.15)) # G5
    disconn_data.extend(generate_sine_wave(659.25, 0.15)) # E5
    disconn_data.extend(generate_sine_wave(523.25, 0.40)) # C5
    save_wav(os.path.join(target_dir, "disconnected.wav"), disconn_data)

if __name__ == "__main__":
    main()
