package diffusion;
/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

import core.Cell;
import diffusion.utils.ElementProvider;
import diffusion.utils.threeDim.GrowableMatrix;
import diffusion.utils.twoDim.Position2D;
import core.Tumor;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * @author Pedro Victori
 */
public abstract class DiffusionLattice implements DiffusionModel {
	private static final double adjustment = 1E3;
	/**
	 * Minimum allowed distance from a voxel containing cells to a boundary
	 */
	protected static final int BUFFER = 10;
	private final GrowableMatrix<Voxel> matrix;
	private final List<Diffusible> diffusibles;
	private final double dv;
	private final ElementProvider<Voxel> voxelProvider;
	private int timeStep;

	/**
	 * Creates all diffusible objects from file, then it creates and populates a new instance of {@code DiffusionLattice} with given dimension.
	 *
	 * @param max         The xyz dimension of the lattice (x=y=z).
	 * @param dv          Voxel size
	 * @param diffusibles A list with all the diffusible substances to be simulated
	 * @param cells       the list of cells to be added to the lattice
	 */
	public DiffusionLattice(int max, double dv, List<Diffusible> diffusibles, List<? extends Cell> cells) {
		this.diffusibles = diffusibles;
		this.dv = dv;

		//every voxel of the matrix will contain a separate Map object with the diffusibles and their concentrations.
		voxelProvider = () -> {
			Voxel element = new Voxel();
			for (Diffusible diffusible : diffusibles) {
				if(diffusible instanceof Drug drug){
					int s = getTimeStep();
					if (s < drug.getStartTime() || s > drug.getEndTime()){
						element.getSubstances().put(diffusible, diffusible.getInitialConcentration());
					} else{ //vortexes created during simulation need to have drug if treatment has already started
						element.getSubstances().put(diffusible, ((Drug) diffusible).getDoseConcentration());
					}
				} else {
					element.getSubstances().put(diffusible, diffusible.getInitialConcentration());
				}
			}
			return element;
		};

		matrix = createMatrix(voxelProvider, max);

		//populate voxels in matrix with their corresponding agents.
		placeCellsInVoxels(cells);
	}

	abstract GrowableMatrix<Voxel> createMatrix(ElementProvider<Voxel> voxelProvider, int max);

	@Override
	public void updateCells(List<? extends Cell> cellList) {
		matrix.forEach(voxel -> voxel.getCellsHere().clear()); //clear old list
		placeCellsInVoxels(cellList);
	}

	/**
	 * Find the voxel that should contain a given cell (or contains it already) according to the cell coordinates.
	 *
	 * @param cell The given cell contained by the voxel
	 * @return A {@code Voxel} that matches the cell coordinates, translated to a position in the diffusion matrix.
	 * @throws IllegalArgumentException if the voxel would be outside the matrix.
	 */
	abstract Voxel findContainingVoxel(Cell cell) throws IllegalArgumentException;

	/**
	 * Whether cell is inside the diffusion matrix (as per its current scope).
	 * Cells who would be place inside the buffer zone, defined as closer to the boundary than the {@code BUFFER} constant,
	 * are not deemed to be inside the matrix.
	 *
	 * @param cell the cell to be evaluated.
	 * @return true if the cell is inside the matrix and its distance to boundary is bigger than or equals to {@code BUFFER}, false otherwise.
	 */
	protected abstract boolean isCellInsideMatrix(Cell cell);

	private void placeCellsInVoxels(List<? extends Cell> cells) {
		boolean allCellsInsideMatrix = cells.stream().allMatch(this::isCellInsideMatrix);
		while (!allCellsInsideMatrix) { //grow the matrix until all cells would be inside the matrix
			matrix.grow(BUFFER, voxelProvider);
			allCellsInsideMatrix = cells.stream().allMatch(this::isCellInsideMatrix);
		}
		for (Cell cell : cells) {
			Voxel voxel = findContainingVoxel(cell);
			voxel.getCellsHere().add(cell);
		}
	}

	@Override
	public void setConcentration(Diffusible substance, Double concentration, int... indexes) throws IllegalArgumentException {
		getVoxelAt(indexes).setConcentration(substance, concentration);
	}

	@Override
	public void changeConcentration(Diffusible substance, Double change, int... indexes) throws IllegalArgumentException {
		getVoxelAt(indexes).changeConcentration(substance, change);
	}

	@Override
	public Map<Diffusible, Double> getSubstancesAt(int... indexes) throws IllegalArgumentException {
		return getVoxelAt(indexes).getSubstances();
	}

	/**
	 * @param indexes two (for a 2D matrix) or three (for a 3D matrix) integers denoting the position of the voxel.
	 * @return the voxel at the position given by the indexes
	 * @throws IllegalArgumentException if indexes contain the wrong number of integers or if the given coordinates don't exist within the matrix.
	 */
	abstract Voxel getVoxelAt(int... indexes) throws IllegalArgumentException;


	Map<Diffusible, Double> computeConcentrationsNp1(Voxel currentVoxel, boolean boundary, int... indexes) {
		Map<Diffusible, Double> concentrationsNp1 = new HashMap<>();
		double cellDensity = currentVoxel.getCellIndex() /(dv*adjustment*1E-18); //convert um^3 to m^3
		for (Diffusible diffusible : diffusibles) {
			double sn = currentVoxel.getSubstances().get(diffusible); //sn denotes concentration (S) in voxel i,j(,k) at time point n, that is, the current concentration at the current position.
			double sn1_ijk;
			if(boundary){
				sn1_ijk = sn; //boundary concentrations don't change
				if(diffusible instanceof Drug drug){ //unless it's a drug
					int s = getTimeStep();
					if (s < drug.getStartTime() || s > drug.getEndTime()){
						sn1_ijk = 0;
					} else{
						sn1_ijk = drug.getDoseConcentration();
					}
				}
			} else {
				//activation or deactivation in cells + consumption and production
				double consumption = 0;
				double production = 0;
				if (cellDensity != 0) {
					if (sn >= diffusible.getThreshold()) {
						consumption = cellDensity * getConsumption(diffusible, sn);
						currentVoxel.getAliveCellsHere().forEach(cell -> cell.consume(diffusible.getInputNode()));
					} else {
						currentVoxel.getAliveCellsHere().forEach(cell -> cell.starve(diffusible.getInputNode()));
					}

					if (diffusible instanceof Factor factor) {
						if(diffusible.getName().equals("lkynr")){
							for(Cell cell : currentVoxel.getCellProductionHere(factor)){
								production += Double.valueOf(Tumor.fbadata.get(cell.cellid))*60*60*2.5E-8*0.001;
							}
						}
						else {
							production = currentVoxel.getCellProductionIndex(factor) * factor.getDefaultProduction();
						}
					}
				}

				//diffusion equation
				double d = diffusible.getDiffusionCoefficient();
				double dv2 = Math.pow(dv * 1E-6, 2); //dv^2, dx=dy=dz=dv //convert um to meters
				double dt = diffusible.getDt();
				sn1_ijk = sn + dt * (d / dv2) * computeNeighboursTerm(diffusible, sn, indexes) +
						dt * (consumption + production);
				if (sn1_ijk < 0) {
					sn1_ijk = 0;
				}
			}
			concentrationsNp1.put(diffusible, sn1_ijk);
		}
		return concentrationsNp1;
	}

	protected abstract double computeNeighboursTerm(Diffusible diffusible, double sn, int... indexes);

	/**
	 * Computes the next diffusion step and return a matrix with the concentration of every diffusible in every voxel at time n+1.
	 *
	 * @param voxelProvider used to create the staging matrix.
	 * @return the matrix with all the concentrations for n+1.
	 */
	abstract GrowableMatrix<Voxel> computeStagingMatrix(ElementProvider<Voxel> voxelProvider);

	/**
	 * Updates concentrations of every substance by one time point (\(n = n+1\)) in every voxel every time it is called, according to the following formula:
	 * \[ S^{n+1}_{i,j,k} = S^n_{i,j,k} + dt * D\left[\frac{S^n_{i+1,j,k}-2S^n_{i,j,k}+S^n_{i-1,j,k}}{dx^2} + \frac{S^n_{i,j+1,k}-2S^n_{i,j,k}+S^n_{i-1,j-1,k}}{dy^2} + \frac{S^n_{i,j,k+1}-2S^n_{i,j,k}+S^n_{i-1,j,k-1}}{dz^2}\right] - R^n_{i,j,k} \]
	 */

	/**
	@Override
	public void update(int timeStep) {
		this.timeStep = timeStep;
		var stagingMatrix = computeStagingMatrix(voxelProvider);
		//update the whole matrix with the staged changes
		//iterators return items in the same order
		Iterator<Voxel> itVoxel = matrix.iterator();
		Iterator<Voxel> itChanges = stagingMatrix.iterator();
		while (itVoxel.hasNext() && itChanges.hasNext()) { //redundant, but do it anyway to catch bugs
			Voxel next = itVoxel.next();
			next.getSubstances().clear();
			next.getSubstances().putAll(itChanges.next().getSubstances());
		}
	}
	*/

	@Override
	public void update(int timeStep) {
		this.timeStep = timeStep;
		Map<String, Map<Diffusible, Double>> beforeDiffusion = getConcentrationsPerVoxel();
		var stagingMatrix = computeStagingMatrix(voxelProvider);
		//update the whole matrix with the staged changes
		//iterators return items in the same order
		Iterator<Voxel> itVoxel = matrix.iterator();
		Iterator<Voxel> itChanges = stagingMatrix.iterator();
		while (itVoxel.hasNext() && itChanges.hasNext()) { //redundant, but do it anyway to catch bugs
			Voxel next = itVoxel.next();
			next.getSubstances().clear();
			next.getSubstances().putAll(itChanges.next().getSubstances());
		}


		// Continue updating the diffusion until average percentage difference is below 0.01%
		Map<Diffusible, Double> averageDifferenceMap = calculateAveragePercentageDifference(beforeDiffusion, getConcentrationsPerVoxel());
		boolean isBelowThreshold = false;
		while (!isBelowThreshold) {
			beforeDiffusion = getConcentrationsPerVoxel();
			stagingMatrix = computeStagingMatrix(voxelProvider);
			itVoxel = matrix.iterator();
			itChanges = stagingMatrix.iterator();
			while (itVoxel.hasNext() && itChanges.hasNext()) {
				Voxel next = itVoxel.next();
				next.getSubstances().clear();
				next.getSubstances().putAll(itChanges.next().getSubstances());
			}

			Map<Diffusible, Double> currentDifferenceMap = calculateAveragePercentageDifference(beforeDiffusion, getConcentrationsPerVoxel());
			for (Diffusible diffusible : currentDifferenceMap.keySet()) {
				double currentPercentageDifference = currentDifferenceMap.get(diffusible);
				if (currentPercentageDifference >= 0.01) {
					isBelowThreshold = false;
					break;
				} else {
					isBelowThreshold = true;
				}
			}
		}
	}

	protected int getTimeStep() {
		return timeStep;
	}

	@Override
	public abstract int getSize();

	@Override
	public double getDv() {
		return dv;
	}

	@Override
	public List<Diffusible> getDiffusibles() {
		return diffusibles;
	}

	/**
	 * Returns the consumption rate
	 *
	 * @param diffusible the substance to be consumed
	 * @param s          the current concentration
	 */
	protected double getConsumption(Diffusible diffusible, double s) {
		double k = diffusible.getDefaultConsumption() * -1;
		return k;
	}

	public Map<Diffusible, Double> calculateAveragePercentageDifference(Map<String, Map<Diffusible, Double>> map1, Map<String, Map<Diffusible, Double>> map2) {
		Map<Diffusible, Double> averageDifferenceMap = new HashMap<>();
		Map<Diffusible, Integer> countMap = new HashMap<>();

		for (String position : map1.keySet()) {
			Map<Diffusible, Double> innerMap1 = map1.get(position);
			Map<Diffusible, Double> innerMap2 = map2.get(position);

			if (innerMap1 != null && innerMap2 != null) {
				for (Diffusible diffusible : innerMap1.keySet()) {
					double value1 = innerMap1.getOrDefault(diffusible, 0.0);
					double value2 = innerMap2.getOrDefault(diffusible, 0.0);

					double difference = value2 - value1;
					double percentageDifference = Math.abs((difference / value1) * 100);

					averageDifferenceMap.put(diffusible, averageDifferenceMap.getOrDefault(diffusible, 0.0) + percentageDifference);
					countMap.put(diffusible, countMap.getOrDefault(diffusible, 0) + 1);
				}
			}
		}

		for (Diffusible diffusible : averageDifferenceMap.keySet()) {
			double averagePercentageDifference = averageDifferenceMap.get(diffusible) / countMap.get(diffusible);
			averageDifferenceMap.put(diffusible, averagePercentageDifference);
		}

		return averageDifferenceMap;
	}
}
