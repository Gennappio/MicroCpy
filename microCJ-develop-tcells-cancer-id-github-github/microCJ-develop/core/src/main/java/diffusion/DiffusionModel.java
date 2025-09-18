/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package diffusion;

import core.Cell;

import java.util.List;
import java.util.Map;

public interface DiffusionModel {

	/**
	 * Sets the concentration for a given substance in a given voxel.
	 *
	 * @param substance     a {@code Diffusible} substance
	 * @param concentration the concentration, as {@code Double}.
	 * @param indexes       two (for a 2D matrix) or three (for a 3D matrix) integers denoting the position of the voxel.
	 * @throws IllegalArgumentException if indexes contains less than two or more than three integers.
	 */
	void setConcentration(Diffusible substance, Double concentration, int... indexes) throws IllegalArgumentException;

	/**
	 * Changes the concentration of a given substance in a given voxel.
	 *
	 * @param substance a {@code Diffusible} substance
	 * @param change    a positive or negative change in concentration, as {@code Double}.
	 * @param indexes   two (for a 2D matrix) or three (for a 3D matrix) integers denoting the position of the voxel.
	 * @throws IllegalArgumentException if indexes contains less than two or more than three integers.
	 */
	void changeConcentration(Diffusible substance, Double change, int... indexes) throws IllegalArgumentException;

	/**
	 * Returns a {@code Map} of all the {@code Diffusible} substances in a given voxel, with their concentrations.
	 *
	 * @param indexes two (for a 2D matrix) or three (for a 3D matrix) integers denoting the position of the voxel.
	 * @return a {@code Map<Diffusible,Double>}, with substances as keys and concentrations as {@code Double}.
	 * @throws IllegalArgumentException if indexes contains less than two or more than three integers or if the given coordinates don't exist within the matrix.
	 */
	Map<Diffusible, Double> getSubstancesAt(int... indexes) throws IllegalArgumentException;

	Map<String, Map<Diffusible, Double>> getConcentrationsPerVoxel();

	/**
	 * Update the model for a new time point.
	 */
	void update(int timeStep);

	/**
	 * Update the list of the cells in the model and their position within the lattice.
	 * @param cellList a list of all agents in the model
	 */
	void updateCells(List<? extends Cell> cellList);

	/**
	 * The size of either side of the lattice.
	 * @return the size of either side of the lattice as an int.
	 */
	int getSize();

	/**
	 * The size of the sides of each voxel.
	 * @return the size of the sides of each voxel as a double.
	 */
	double getDv();

	/**
	 * A list of all the {@code Diffusible} objects present in the model.
	 * @return A {@code List<Diffusible>}.
	 */
	List<Diffusible> getDiffusibles();
}
