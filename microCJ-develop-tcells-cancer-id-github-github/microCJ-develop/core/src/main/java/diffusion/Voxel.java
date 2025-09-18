/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

package diffusion;

import core.Agent;
import core.Cell;
import core.Cell3D;
import core.Identifier;

import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.Stream;

class Voxel extends Identifier {
	private final Map<Diffusible, Double> substances;
	private final List<Cell> cellsHere;
	private static final boolean testing = true;
	private static final String stTesting = "Voxel: ";

	Voxel() {
		substances = new HashMap<>();
		cellsHere = new ArrayList<>();
	}

	List<Cell> getCellsHere() {
		return cellsHere;
	}

	Map<Diffusible, Double> getSubstances() {
		return substances;
	}

	/**
	 * Returns the cell index. Cell index = [normal, alive cells] + 0.5 [arrested, alive cells]. This is used to calculate consumption in a voxel.
	 * @return the cell index as a double
	 */
	double getCellIndex(){
		return cellsHere.stream().filter(Cell::isAlive).mapToDouble(cell -> cell.isArrested() ? 0.5 : 1).sum();
	}

	/**
	 * Returns the cell production index for a given diffusible factor. Cell production index = [normal, alive cells producing the factor (expressing the output node for that factor)] + 0.5 [arrested, alive cells producing the factor]. This is used to calculate production in a voxel.
	 * @param factor the Factor for which production index is to be calculated
	 * @return the cell production index as a double
	 */
	double getCellProductionIndex(Factor factor){
		return cellsHere.stream().filter(Cell::isAlive).filter(cell -> cell.isExpressing(factor.getOutputNode())).mapToDouble(cell -> cell.isArrested() ? 0.5 : 1).sum();
	}
	List<Cell> getCellProductionHere(Factor factor){
		return cellsHere.stream().filter(Cell::isAlive).filter(cell -> cell.isExpressing(factor.getOutputNode())).collect(Collectors.toList());
	}

	Stream<Cell> getAliveCellsHere(){
		return cellsHere.stream().filter(Cell::isAlive);
	}

	/**
	 * Sets the concentration for a given substance.
	 * @param substance a {@code Diffusible} substance
	 * @param concentration the concentration, as {@code Double}.
	 */
	void setConcentration(Diffusible substance, Double concentration) {
		substances.put(substance, concentration);
	}

	/**
	 *  Changes the concentration of a given substance.
	 * @param substance a {@code Diffusible} substance
	 * @param change a positive or negative change in concentration, as {@code Double}.
	 */
	void changeConcentration(Diffusible substance, Double change) {
		substances.put(substance, substances.get(substance) + change);
	}

	@Override
	public String toString() {
		StringBuilder stringBuilder = new StringBuilder("Voxel - ID: " + getId() + ". Number of cells: " + cellsHere.size() + ". Substances ->");
		substances.forEach((key, value) -> stringBuilder.append(" [").append(key.getName()).append("] = ").append(value));
		return stringBuilder.toString();
	}
}
