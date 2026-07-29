make_io_sites -horizontal_site IO_SIDE \
        -vertical_site IO_TOP \
        -corner_site IO_CORNER \
        -offset 0 \
        -rotation_vertical R90
place_pin -pin_name /component/pump1 -layer met10 -location { 960 660 } -pin_size { 40 40 }
place_pin -pin_name /component/pump2 -layer met10 -location { 960 750 } -pin_size { 40 40 }
place_pin -pin_name /component/pump3 -layer met10 -location { 960 840 } -pin_size { 40 40 }
place_pin -pin_name /component/pump4 -layer met10 -location { 960 930 } -pin_size { 40 40 }
place_pin -pin_name /component/control.fluid_in3 -layer met10 -location { 1050 660 } -pin_size { 40 40 }
place_pin -pin_name /component/control.fluid_in2 -layer met10 -location { 1050 750 } -pin_size { 40 40 }
place_pin -pin_name /component/control.fluid_in1 -layer met10 -location { 1050 840 } -pin_size { 40 40 }
place_pin -pin_name /component/pump5 -layer met10 -location { 1050 930 } -pin_size { 40 40 }
place_pin -pin_name /component/control.circulate_in -layer met10 -location { 1140 660 } -pin_size { 40 40 }
place_pin -pin_name /component/control.circulate2 -layer met10 -location { 1140 750 } -pin_size { 40 40 }
place_pin -pin_name /component/control.circulate3 -layer met10 -location { 1140 840 } -pin_size { 40 40 }
place_pin -pin_name /component/control.filter1 -layer met10 -location { 1140 930 } -pin_size { 40 40 }
place_pin -pin_name /component/control.filter2 -layer met10 -location { 1230 660 } -pin_size { 40 40 }
place_pin -pin_name /component/control.circulate1 -layer met10 -location { 1230 750 } -pin_size { 40 40 }
place_pin -pin_name /component/control.flush1 -layer met10 -location { 1230 840 } -pin_size { 40 40 }
place_pin -pin_name /component/control.circulate_out -layer met10 -location { 1230 930 } -pin_size { 40 40 }
place_pin -pin_name /component/control.flush2 -layer met10 -location { 1320 660 } -pin_size { 40 40 }
place_pin -pin_name /component/control.stage -layer met10 -location { 1320 750 } -pin_size { 40 40 }
place_pin -pin_name /component/control.flush3 -layer met10 -location { 1320 840 } -pin_size { 40 40 }
place_pin -pin_name /component/control.out -layer met10 -location { 1410 750 } -pin_size { 40 40 }
place_pin -pin_name /component/control.filter4 -layer met10 -location { 1410 840 } -pin_size { 40 40 }
place_pin -pin_name /component/control.filter3 -layer met10 -location { 1410 930 } -pin_size { 40 40 }
place_io_terminals */pad
remove_io_rows
