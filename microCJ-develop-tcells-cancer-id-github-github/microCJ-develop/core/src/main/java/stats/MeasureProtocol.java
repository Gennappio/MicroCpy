/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package stats;

import core.Cell;
import core.Fate;
import graph.Subpopulation;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Enum containing all the possible measures that can be taken, along with their implementations of the functional interface MeasureTaker
 * @author Pedro Victori
 */
enum MeasureProtocol {
	ALIVE_CELL_COUNT((world, noOption) -> {
		String header = "cell count";
		return new Measure(header, Integer.toString(world.getTumor().getTotalAliveCount()));
	}, false),

	ALIVE_CELL_COUNT_BY_GROUP((world, noOption) -> {
		return new Measure(world.getTumor().getSubpopulationAliveCounts());
	}, false),

	CELLS_EXPRESSING_NODE((world, option) -> {
		return new Measure("number of cells expressing " + option,
				Long.toString(world.getTumor().getCellList().stream().filter(cell -> cell.isExpressing(option)).count()));

	}, true),

	CELLS_EXPRESSING_NODE_BY_GROUP((world, option) -> {
		//obtains a map of mutation group names and counts of the cells in every group expressing the gene
		Map<String, Integer> counts = world.getTumor().getMutationGroups().stream().collect(Collectors.toMap(Subpopulation::getName,
				mutationGroup -> (int) world.getTumor().getCellList().stream().filter(cell -> cell.isExpressing(option)) //filtering all cells expressing the gene
			.filter(cell -> Objects.equals(cell.getSubpopulationName().orElse(null), mutationGroup.getName())).count())); //filtering cells by mutation group, or null

		return new Measure(counts, "", " expressing " + option);
	}, true),

	CELL_FATES((world, noOption) -> {
		Map<String, Integer> counts = Arrays.stream(Fate.values()).collect(Collectors.toMap(
				Fate::toString,
				fate -> (int) world.getTumor().getCellList().stream()
						.filter(cell -> cell.getLastActivatedFate().equals(fate)).count()));
		counts.put("apoptosis", world.getTumor().getDeadCellsAtLastStep().values().stream().mapToInt(v -> v).sum());
		return new Measure(counts);
	}, false),

	CELL_FATES_BY_GROUP((world, noOption) -> {
		Map<String, Integer> counts = new HashMap<>();
		for (Subpopulation group : world.getTumor().getMutationGroups()) {
			var groupCounts = Arrays.stream(Fate.values()).collect(Collectors.toMap(
					fate -> group.getName() + "_" + fate.toString(),
					fate -> (int) world.getTumor().getCellList().stream()
							.filter(cell -> cell.getLastActivatedFate().equals(fate))
							.filter(cell -> Objects.equals(cell.getSubpopulation().orElse(null), group))
							.count()));
			groupCounts.put(group.getName() + "_apoptosis", world.getTumor().getDeadCellsAtLastStep().getOrDefault(group,0));
			counts.putAll(groupCounts);

		}
		return new Measure(counts);
	}, false),

	REAL_TIME((world, noOption) ->{
		return new Measure("real time",
				Long.toString(world.getElapsed()/1000000));
	}, false),

	NECROTIC_CELL_COUNT((world, noOption) -> {
		return new Measure("necrotic count", Long.toString(world.getTumor().getCellList().stream().filter(Cell::isNecrotic).count()));
	}, false);

	private final MeasureTaker measuringProcedure;
	private final boolean needsOption;

	MeasureProtocol(MeasureTaker measuringProcedure, boolean needsOption) {
		this.needsOption = needsOption;
		this.measuringProcedure = measuringProcedure;
	}

	/**
	 * Returns the implementation of the functional interface MeasureTaker
	 * @return the implementation of the functional interface MeasureTaker
	 */
	MeasureTaker getMeasuringProcedure() {
		return measuringProcedure;
	}

	/**
	 * Whether an option is needed to take the measure.
	 * @return a boolean, true if an option is needed, false otherwise.
	 */
	boolean needsOption() {
		return needsOption;
	}

	@Override
	public String toString() {
		return "MeasureProtocol{" +
				"measuringProcedure=" + name() +
				", needsOption=" + needsOption +
				'}';
	}
}
