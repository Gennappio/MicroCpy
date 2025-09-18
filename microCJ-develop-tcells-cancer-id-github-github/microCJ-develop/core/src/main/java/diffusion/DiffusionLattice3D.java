package diffusion;
/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

import core.Cell;
import core.Cell3D;
import diffusion.utils.ElementProvider;
import diffusion.utils.threeDim.ArrayMatrix3D;
import diffusion.utils.threeDim.GrowableMatrix;
import diffusion.utils.threeDim.Matrix3D;
import diffusion.utils.threeDim.Position3D;
import diffusion.utils.twoDim.Position2D;
import geom.threeDim.Point3D;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author Pedro Victori
 */
public final class DiffusionLattice3D extends DiffusionLattice {
	private Matrix3D<Voxel> matrix;

	/**
	 * Creates all diffusible objects from file, then it creates and populates a new instance of {@code DiffusionLattice} with given dimension.
	 *
	 * @param max         The xyz dimension of the lattice (x=y=z).
	 * @param dv          Voxel size
	 * @param diffusibles A list with all the diffusible substances to be simulated
	 * @param cells       the list of cells to be added to the lattice
	 */
	public DiffusionLattice3D(int max, double dv, List<Diffusible> diffusibles, List<? extends Cell> cells) {
		super(max, dv, diffusibles, cells);
		if (!cells.stream().allMatch(cell -> cell instanceof Cell3D))
			throw new IllegalArgumentException("All elements in 'cells' need to be Cell3D");
	}

	@Override
	public void updateCells(List<? extends Cell> cellList) {
		if (!cellList.stream().allMatch(cell -> cell instanceof Cell3D))
			throw new IllegalArgumentException("All elements in 'cells' need to be Cell3D");
		super.updateCells(cellList);
	}

	@Override
	protected GrowableMatrix<Voxel> createMatrix(ElementProvider<Voxel> voxelProvider, int max) {
		matrix = new ArrayMatrix3D<>(voxelProvider, max);
		return matrix;
	}

	@Override
	protected Voxel findContainingVoxel(Cell cell) throws IllegalArgumentException {
		return matrix.get(cellToPosition(cell));
	}

	@Override
	protected boolean isCellInsideMatrix(Cell cell) {
		try {
			var pos = cellToPosition(cell);
			return pos.shortestToBoundary() >= BUFFER;
		} catch (IllegalArgumentException iae) {
			return false;
		}
	}

	private Position3D cellToPosition(Cell cell) throws IllegalArgumentException {
		return matrix.getScope().pointToPosition((Point3D) cell.getLocation(), getDv());
	}

	@Override
	protected Voxel getVoxelAt(int... indexes) throws IllegalArgumentException {
		if (indexes.length != 3)
			throw new IllegalArgumentException("This method must receive three indexes: i, j, k coordinates");
		return matrix.get(indexes[0], indexes[1], indexes[2]);
	}

	@Override
	protected double computeNeighboursTerm(Diffusible diffusible, double sn_ijk, int... indexes) {
		int i = indexes[0];
		int j = indexes[1];
		int k = indexes[2];
		double sn_ip1jk = matrix.get(i + 1, j, k).getSubstances().get(diffusible); //sn at i+1, j, k
		double sn_im1jk = matrix.get(i - 1, j, k).getSubstances().get(diffusible);
		double sn_ijp1k = matrix.get(i, j + 1, k).getSubstances().get(diffusible);
		double sn_ijm1k = matrix.get(i, j - 1, k).getSubstances().get(diffusible);
		double sn_ijkp1 = matrix.get(i, j, k + 1).getSubstances().get(diffusible);
		double sn_ijkm1 = matrix.get(i, j, k - 1).getSubstances().get(diffusible);
		return -6 * sn_ijk + sn_ip1jk + sn_im1jk + sn_ijp1k + sn_ijm1k + sn_ijkp1 + sn_ijkm1;
	}

	@Override
	protected GrowableMatrix<Voxel> computeStagingMatrix(ElementProvider<Voxel> voxelProvider) {
		//Changes for next time point are stored in this matrix, then moved all at once to the main matrix.
		Matrix3D<Voxel> stagedChanges = new ArrayMatrix3D<>(voxelProvider, matrix.getScope().getMax());
		for (Position3D position3D : matrix.getScope()) { // loops all voxels
			Voxel currentVoxel = matrix.get(position3D);
			var concentrationsNp1 = computeConcentrationsNp1(currentVoxel, position3D.isAtBoundary(),
					position3D.getI(), position3D.getJ(), position3D.getK());
			//replaces the concentration at n with concentration at n+1 in the stagedChangesMatrix
			stagedChanges.get(position3D).getSubstances().replaceAll((diffusible, oldConcentration) -> concentrationsNp1.get(diffusible));
		}
		return stagedChanges;
	}

	@Override
	public Map<String, Map<Diffusible, Double>> getConcentrationsPerVoxel(){
		Map<String, Map<Diffusible, Double>> map = new HashMap<>();
		for (Position3D position3D : matrix.getScope()) {
			map.put(position3D.toCSV(), matrix.get(position3D).getSubstances());
		}
		return map;
	}

	@Override
	public int getSize() {
		return matrix.getScope().getMax();
	}
}
