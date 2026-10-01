INPUTS = \
	benchmarks/multiplex_toilet/multiplex_toilet.v \
	benchmarks/ChIP/ChIP_pads_4.v \
	benchmarks/mnacidpro/mnacidpro_pads_1.v \
	benchmarks/mnacidpro/mnacidpro_pads_2.v \
	benchmarks/mnacidpro/mnacidpro_pads_3.v \
	benchmarks/mnacidpro/mnacidpro_pads_4.v \
	benchmarks/mrnaiso/mRNAiso_pads_1.v \
	benchmarks/mrnaiso/mRNAiso_pads_2.v \
	benchmarks/mrnaiso/mRNAiso_pads_3.v \
	benchmarks/mrnaiso/mRNAiso_pads_4.v \
	benchmarks/kinase/kinase_1.v \
	benchmarks/kinase/kinase_2.v \
	benchmarks/kinase/kinase_3.v \
	benchmarks/kinase/kinase_4.v
	# benchmarks/ChIP/ChIP_pads_10.v \

# poor results for: ica incpca mds_nm pca grp smacof_nm spectral
DIM_ALGS=mds smacof isomap
RUNS = exact ilp torch ${DIM_ALGS}
RESULTS = $(INPUTS:%.v=%.pdf)
RENDERED = $(foreach RUN,${RUNS},$(INPUTS:%.v=%.${RUN}.scad))

all: $(RESULTS) $(RENDERED)

benchmarks/library.v: benchmarks/kinase_activity.v benchmarks/kinase_pads.v benchmarks/mnacidpro.v benchmarks/mRNAiso.v benchmarks/mnacidpro_pads.v benchmarks/mRNAiso_pads.v benchmarks/ChIP.v benchmarks/ChIP_pads.v
	cat $^ > $@

.PRECIOUS: %.json %.torch.csv %.torch_eq.csv %.exact.csv %.mds.csv %.ilp.csv %.smacof.csv %.isomap.csv

PYTHON3 = python3

%.mp4 %.gif: %.iter.csv %.json render_flat.py
	${PYTHON3} render_flat.py $< --graph $*.json --output $@ \
		--logfile $*.render_flat.log 2>&1 >> $*.render_flat.err.log

%.scad: %.csv %.json render.py
	${PYTHON3} render.py $< --graph $*.json --output $@ \
		--logfile $*.render.log 2>&1 >> $*.render.err.log

benchmarks/picorv32.json: benchmarks/picorv32.v
	yosys -p "read_verilog $<; synth -top picorv32; write_json $@"

%.json: %.v benchmarks/library.v
	yosys -p "read_verilog benchmarks/library.v; read_verilog $<; hierarchy -top thing; proc; flatten; clean -purge; write_json $@" > $*.log

%.pdf: %.json stats.py %.torch_eq.csv %.exact.csv %.ilp.csv %.torch.csv %.mds.csv %.isomap.csv %.smacof.csv
	${PYTHON3} stats.py --graph $*.json --output $@ \
		--logfile $*.stats.log 2>&1 >> $*.stats.err.log \
 		$(filter %.csv, $^)

%.torch.json: %.json
	cp $< $@

%.torch_eq.json: %.json
	cp $< $@

%.simulation.json: %.json
	cp $< $@

%.horizontal.json: %.json
	cp $< $@

%.exact.json: %.json
	cp $< $@

%.ilp.json: %.json
	cp $< $@

define DIMENSION =
%.${1}.json: %.json
	cp $$< $$@

%.${1}.csv %.${1}.timer %.${1}.log: %.${1}.json dimension.py
	date --iso-8601=seconds >> $$*.${1}.timer
	$${PYTHON3} dimension.py \
		--graph $$*.${1}.json \
		--alg ${1} \
		--output $$*.${1}.csv \
		--logfile $$*.${1}.log 2>&1 >> $$*.${1}.err.log
	date --iso-8601=seconds >> $$*.${1}.timer
endef
$(foreach ALG,${DIM_ALGS},$(eval $(call DIMENSION,${ALG})))

%.torch.csv %.torch.timer %.torch.log %.torch.iter.csv: %.torch.json matrix.py
	date --iso-8601=seconds >> $*.torch.timer
	${PYTHON3} matrix.py --graph $< \
		--output $*.torch.csv \
		--autograde --dynamic --cutoff 1 --iterations 5000 \
		--logfile $*.torch.log 2>&1 >> $*.torch.err.log \
		--intermediate $*.torch.iter.csv
	date --iso-8601=seconds >> $*.torch.timer

%.torch_eq.csv %.torch_eq.timer %.torch_eq.log %.torch_eq.iter.csv: %.torch_eq.json matrix.py
	date --iso-8601=seconds >> $*.torch_eq.timer
	${PYTHON3} matrix.py --graph $< \
		--output $*.torch_eq.csv \
		--autograde --dynamic --cutoff 1 --iterations 5000 \
		--distance equidistant \
		--logfile $*.torch_eq.log 2>&1 >> $*.torch_eq.err.log \
		--intermediate $*.torch_eq.iter.csv
	date --iso-8601=seconds >> $*.torch_eq.timer

%.simulation.csv %.simulation.timer %.simulation.log %.simulation.iter.csv: %.simulation.json simulation.py
	date --iso-8601=seconds >> $*.simulation.timer
	${PYTHON3} simulation.py --graph $< \
		--output $*.simulation.csv \
		--intermediate $*.simulation.iter.csv \
		--logfile $*.simulation.log 2>&1 >> $*.simulation.err.log
	date --iso-8601=seconds >> $*.simulation.timer

%.exact.csv %.exact.timer %.exact.log: %.json exact.py
	date --iso-8601=seconds >> $*.exact.timer
	${PYTHON3} exact.py $< \
		--output $@ \
		--timeout 86400 \
		--cache $*.exact.cip \
		--logfile $*.exact.log 2>&1 >> $*.exact.err.log
	date --iso-8601=seconds >> $*.exact.timer

%.ilp.csv %.ilp.timer %.ilp.log: %.json exact.py
	date --iso-8601=seconds >> $*.ilp.timer
	${PYTHON3} exact.py $< \
		--output $@ \
		--timeout 86400 \
		--minimize \
		--cache $*.ilp.cip \
		--logfile $*.ilp.log 2>&1 >> $*.ilp.err.log
	date --iso-8601=seconds >> $*.ilp.timer

%.pdf: %.dot
	dot -Tpdf -o $@ $<

clean_stats:
	rm -f benchmarks/kinase/*.pdf
	rm -f benchmarks/mrnaiso/*.pdf
	rm -f benchmarks/multiplex_toilet/*.pdf
	rm -f benchmarks/mnacidpro/*.pdf
	rm -f benchmarks/ChIP/*.pdf

clean_render:
	rm -f benchmarks/kinase/*.scad
	rm -f benchmarks/mrnaiso/*.scad
	rm -f benchmarks/multiplex_toilet/*.scad
	rm -f benchmarks/mnacidpro/*.scad
	rm -f benchmarks/ChIP/*.scad

clean_data:
	rm -f benchmarks/kinase/*.csv
	rm -f benchmarks/mrnaiso/*.csv
	rm -f benchmarks/multiplex_toilet/*.csv
	rm -f benchmarks/mnacidpro/*.csv
	rm -f benchmarks/ChIP/*.csv

clean_logs:
	rm -f benchmarks/kinase/*.log
	rm -f benchmarks/mrnaiso/*.log
	rm -f benchmarks/multiplex_toilet/*.log
	rm -f benchmarks/mnacidpro/*.log
	rm -f benchmarks/ChIP/*.log
	rm -f benchmarks/kinase/*.timer
	rm -f benchmarks/mrnaiso/*.timer
	rm -f benchmarks/multiplex_toilet/*.timer
	rm -f benchmarks/mnacidpro/*.timer
	rm -f benchmarks/ChIP/*.timer

clean: clean_stats clean_render clean_data clean_logs
