from elftools.elf.elffile import ELFFile
import capstone

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    elf = ELFFile(f)
    for sec in elf.iter_sections():
        if sec['sh_addr'] <= 0x69340 < sec['sh_addr'] + sec['sh_size']:
            sec_addr = sec['sh_addr']
            sec_data = sec.data()
            off = 0x69340 - sec_addr
            chunk = sec_data[off:off+2048]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            print("=== Tracing lora in 0x69340 ===")
            for ins in md.disasm(chunk, 0x69340):
                if '0x130' in ins.op_str:
                    print(f"  0x{ins.address:x}: {ins.mnemonic}\t{ins.op_str}")
