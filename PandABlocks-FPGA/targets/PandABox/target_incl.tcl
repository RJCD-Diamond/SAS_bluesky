set FPGA_PART xc7z030sbg485-1
set HDL_TOP PandABox_top

# Target specific Constriants to be read
# NB: we could just read the entire directory with 'add_files [glob $TARGET_DIR/const/*.xdc]
set CONSTRAINTS {                   \
            PandABox-pins_impl.xdc  \
            PandABox-freq.xdc       \
            PandABox-clks_impl.xdc
}

