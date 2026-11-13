PYTHON3 = python3

INPUTS = benchmarks/multiplex_toilet/multiplex_toilet.v \
	benchmarks/ChIP/ChIP_pads_4.v \
	benchmarks/ChIP/ChIP_pads_10.v \
	benchmarks/mnacidpro/mnacidpro_pads_3.v \
	benchmarks/mrnaiso/mRNAiso_pads_4.v \
	benchmarks/kinase/kinase_4.v \
	benchmarks/iscas85/c432.v \
	benchmarks/iscas85/c499.v \
	benchmarks/iscas85/c880.v \
	benchmarks/iscas85/c1355.v \
	benchmarks/iscas85/c1908.v \
	benchmarks/picorv32/picorv32.v
# 	benchmarks/mnacidpro/mnacidpro_pads_1.v \
# 	benchmarks/mnacidpro/mnacidpro_pads_2.v \
# 	benchmarks/mnacidpro/mnacidpro_pads_4.v \
# 	benchmarks/mrnaiso/mRNAiso_pads_1.v \
# 	benchmarks/mrnaiso/mRNAiso_pads_2.v \
# 	benchmarks/mrnaiso/mRNAiso_pads_3.v \
# 	benchmarks/kinase/kinase_1.v \
# 	benchmarks/kinase/kinase_2.v \
# 	benchmarks/kinase/kinase_3.v

VERILOG_LIBRARIES = benchmarks/kinase_activity.v \
	benchmarks/kinase_pads.v \
	benchmarks/mnacidpro.v \
	benchmarks/mRNAiso.v \
	benchmarks/mnacidpro_pads.v \
	benchmarks/mRNAiso_pads.v \
	benchmarks/ChIP.v \
	benchmarks/ChIP_pads.v

# poor results for: ica incpca mds_nm pca grp smacof_nm spectral
DIM_ALGS=mds smacof isomap pca spectral
ALGORITHMS = torch torch_brute torch_autograde ${DIM_ALGS}

REPORTS = $(INPUTS:%.v=%.pdf)
RUNS = ${shell seq 0 7}
RESULTS = \
		$(foreach ALGORITHM,${ALGORITHMS}, \
		$(foreach RUN,${RUNS}, \
		$(INPUTS:%.v=%.run_${RUN}.${ALGORITHM}.csv)))
RENDERED = $(RESULTS:%.csv=%.scad)
STATS = $(INPUTS:%.v=%.stats.csv)

all: $(RESULTS) $(RENDERED) $(REPORTS)

results: $(RESULTS)

reports: $(REPORTS)

stats: $(STATS)

COLUMBA_V = $(wildcard benchmarks/columba/*.v)
COLUMBA_STATS = $(COLUMBA_V:%.v=%.torch.stats.csv)
COLUMBA_RENDER = $(COLUMBA_V:%.v=%.torch.scad)
COLUMBA_ENERGY = $(COLUMBA_V:%.v=%.torch.energy.csv)

benchmarks/columba/stats.csv: ${COLUMBA_STATS}
	tail -q -n 1 $^ > $@

columba: $(COLUMBA_RENDER) benchmarks/columba/stats.csv

run_count :
	@ echo ${RESULTS} | tr ' ' '\n' | wc -l

benchmarks/library.v: ${VERILOG_LIBRARIES}
	cat $^ > $@

%.mp4 %.gif: %.iter.csv %.json render_flat.py
	${PYTHON3} render_flat.py $< --graph $*.json --output $@ \
		--logfile $*.render_flat.log 2>&1 >> $*.render_flat.err.log

%.scad: %.csv %.json render.py
	${PYTHON3} render.py $< --graph $*.json --output $@ \
		--logfile $*.render.log 2>&1 >> $*.render.err.log

benchmarks/columba/%.scad: benchmarks/columba/%.csv benchmarks/columba/%.json render.py
	${PYTHON3} render.py $< --graph benchmarks/columba/$*.json --output $@ \
		--implicit_pinholes \
		--logfile benchmarks/columba/$*.render.log 2>&1 >> benchmarks/columba/$*.render.err.log

%.json: %.v benchmarks/library.v
	yosys -p "read_verilog benchmarks/library.v; read_verilog $<; hierarchy -top thing; proc; flatten; clean -purge; write_json $@" > $*.log

STATS_DEP = \
		$(foreach ALGORITHM,${ALGORITHMS}, \
		$(foreach RUN,${RUNS}, \
		 	%.run_${RUN}.${ALGORITHM}.csv))
%.pdf: %.json stats.py ${STATS_DEP}
	${PYTHON3} stats.py --graph $*.json --output $@ \
		--logfile $*.pdf.log \
 		$(filter %.csv, $^) \
		2>&1 >> $*.pdf.err.log

%.stats.csv: %.json analysis.py ${STATS_DEP}
	${PYTHON3} analysis.py --graph $*.json --output $@\
		--logfile $*.stats.log \
 		$(filter %.csv, $^) \
		2>&1 >> $*.pdf.err.log

define JSON_COPY =
%.${1}.json: %.json
	cp $$< $$@
endef
$(foreach ALGORITHM,${ALGORITHMS}, \
	$(eval $(call JSON_COPY,${ALGORITHM})))
$(foreach ALGORITHM,${ALGORITHMS}, \
	$(foreach RUN,${RUNS}, \
	$(eval $(call JSON_COPY,run_${RUN}.${ALGORITHM}))))

define DIMENSION =
%.${1}.csv %.${1}.timer &: %.${1}.json
	date --iso-8601=seconds > $$*.${1}.timer
	$${PYTHON3} dimension.py \
		--graph $$*.${1}.json \
		--alg ${1} \
		--output $$*.${1}.csv \
		--logfile $$*.${1}.log 2>&1 >> $$*.${1}.err.log
	date --iso-8601=seconds >> $$*.${1}.timer
endef
$(foreach ALG,${DIM_ALGS},$(eval $(call DIMENSION,${ALG})))

TORCH_ARGS= --cutoff_kinetic 0.01 --iterations 50000 --tick 0.001 \
	--dynamic --dyn_range 200 --dyn_height 10

benchmarks/columba/torch.timing.csv: ${COLUMBA_ENERGY}
	python3 torch_timing.py $@ $^

benchmarks/columba/%.torch.csv benchmarks/columba/%.torch.timer benchmarks/columba/%.torch.energy.csv &: benchmarks/columba/%.torch.json
	date --iso-8601=seconds > benchmarks/columba/$*.torch.timer
	${PYTHON3} matrix.py --graph $< \
		--output benchmarks/columba/$*.torch.csv \
		--cutoff_potential 0.5 --cutoff_kinetic 0.01 --iterations 50000 --tick 0.001 \
		--dynamic --dyn_range 100 --dyn_height 10 \
		--collision_crank 0.1 --init_vel 1.0 \
		--damping 0.92 \
		--energy benchmarks/columba/$*.torch.energy.csv \
		--logfile benchmarks/columba/$*.torch.log 2>&1 >> benchmarks/columba/$*.torch.err.log
	date --iso-8601=seconds >> benchmarks/columba/$*.torch.timer

benchmarks/columba/%.torch.stats.csv: benchmarks/columba/%.json analysis.py benchmarks/columba/%.torch.csv
	${PYTHON3} analysis.py --graph $< --output $@ $(filter %.csv, $^)

benchmarks/picorv32/picorv32.%.torch.csv benchmarks/picorv32/picorv32.%.torch.timer benchmarks/picorv32/picorv32.%.torch.energy.csv &: benchmarks/picorv32/picorv32.%.torch.json
	date --iso-8601=seconds > benchmarks/picorv32/picorv32.$*.torch.timer
	${PYTHON3} matrix.py --graph $< \
		--output benchmarks/picorv32/picorv32.$*.torch.csv \
		--cutoff_kinetic 1 --iterations 0 --tick 0.0002 \
		--dynamic --dyn_range 100 --dyn_height 10 \
		--damping 0.85 \
		--energy benchmarks/picorv32/picorv32.$*.torch.energy.csv \
		--logfile benchmarks/picorv32/picorv32.$*.torch.log 2>&1 >> benchmarks/picorv32/picorv32.$*.torch.err.log
	date --iso-8601=seconds >> benchmarks/picorv32/picorv32.$*.torch.timer

benchmarks/picorv32/picorv32.%.torch_brute.csv benchmarks/picorv32/picorv32.%.torch_brute.timer benchmarks/picorv32/picorv32.%.torch_brute.energy.csv &: benchmarks/picorv32/picorv32.%.torch_brute.json
	date --iso-8601=seconds > benchmarks/picorv32/picorv32.$*.torch_brute.timer
	${PYTHON3} matrix.py --graph $< \
		--output benchmarks/picorv32/picorv32.$*.torch_brute.csv \
		--cutoff_kinetic 1 --iterations 0 --tick 0.0002 \
		--dynamic --dyn_range 100 --dyn_height 10 \
		--damping 0.85 \
		--distance euclidean_brute \
		--energy benchmarks/picorv32/picorv32.$*.torch_brute.energy.csv \
		--logfile benchmarks/picorv32/picorv32.$*.torch_brute.log 2>&1 >> benchmarks/picorv32/picorv32.$*.torch_brute.err.log
	date --iso-8601=seconds >> benchmarks/picorv32/picorv32.$*.torch_brute.timer

%.torch.csv %.torch.timer %.torch.energy.csv &: %.torch.json
	date --iso-8601=seconds > $*.torch.timer
	${PYTHON3} matrix.py --graph $< \
		--output $*.torch.csv \
		${TORCH_ARGS} \
		--energy $*.torch.energy.csv \
		--logfile $*.torch.log 2>&1 >> $*.torch.err.log
	date --iso-8601=seconds >> $*.torch.timer


%.torch_crank.csv %.torch_crank.timer %.torch_crank.energy.csv &: %.torch_crank.json
	date --iso-8601=seconds > $*.torch_crank.timer
	${PYTHON3} matrix.py --graph $< \
		--output $*.torch_crank.csv \
		${TORCH_ARGS} \
		--collision_crank \
		--energy $*.torch_crank.energy.csv \
		--logfile $*.torch_crank.log 2>&1 >> $*.torch_crank.err.log
	date --iso-8601=seconds >> $*.torch_crank.timer

%.torch_eq.csv %.torch_eq.timer %.torch_eq.energy.csv &: %.torch_eq.json
	date --iso-8601=seconds > $*.torch_eq.timer
	${PYTHON3} matrix.py --graph $< \
		--output $.torch_eq.csv \
		${TORCH_ARGS} \
		--distance equidistant \
		--energy $*.torch_eq.energy.csv \
		--logfile $*.torch_eq.log 2>1 >> $*.torch_eq.err.log
	date --iso-8601=seconds >> $*.torch_eq.timer

%.torch_brute.csv %.torch_brute.timer %.torch_brute.energy.csv &: %.torch_brute.json
	date --iso-8601=seconds > $*.torch_brute.timer
	${PYTHON3} matrix.py --graph $< \
		--output $*.torch_brute.csv \
		${TORCH_ARG} \
		--distance euclidean_brute \
		--energy $*.torch_brute.energy.csv \
		--logfile $*.torch_brute.log 2>&1 >> $*.torch_brute.err.log
	date --iso-8601=seconds >> $*.torch_brute.timer

%.torch_autograde.csv %.torch_autograde.timer %.torch_autograde.energy.csv &: %.torch_autograde.json
	date --iso-8601=seconds > $*.torch_autograde.timer
	${PYTHON3} matrix.py --graph $< \
		--output $*.torch_autograde.csv \
		${TORCH_ARGS} \
		--autograde \
		--energy $*.torch_autograde.energy.csv \
		--logfile $*.torch_autograde.log 2>&1 >>$*.torch_autograde.err.log
	date --iso-8601=seconds >> $*.torch_autograde.timer

%.exact.csv %.exact.timer %.exact.cip &: %.exact.json exact.py
	date --iso-8601=seconds > $*.exact.timer
	${PYTHON3} exact.py $< \
		--output $@ \
 		--timeout 1800 \
		--cache $*.exact.cip \
		--logfile $*.exact.log 2>&1 >> $*.exact.err.log
	date --iso-8601=seconds >> $*.exact.timer

%.ilp.csv %.ilp.timer %.ilp.cip &: %.json exact.py
	date --iso-8601=seconds > $*.ilp.timer
	${PYTHON3} exact.py $< \
		--output $@ \
		--timeout 1800 \
		--minimize \
		--cache $*.ilp.cip \
		--logfile $*.ilp.log 2>&1 > $*.ilp.err.log
	date--iso-8601=seconds >> $*.ilp.timer

%.v %.dot %_combined.txt: %.txt benchmarks/columba/rule.txt
	cat $^ > $*_combined.txt
	${PYTHON3} columba.py $*_combined.txt $*.v

%.graph.pdf: %.dot
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
	rm -f benchmarks/mnaidpro/*.scad
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

.PHONY: clean clean_stats clean_logs clean_data clean_render all render run_count results reports stats columba

# with no prerequisites, set all intermediate argets as SECONDARY
.SECONDARY:
