package diffusion;

import core.Cell;
import core.Cell2D;
import diffusion.utils.ElementProvider;
import diffusion.utils.threeDim.GrowableMatrix;
import diffusion.utils.twoDim.ArrayMatrix2D;
import diffusion.utils.twoDim.Matrix2D;
import diffusion.utils.twoDim.Position2D;
import geom.twoDim.Point2D;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class DiffusionLattice2D extends DiffusionLattice {
	private Matrix2D<Voxel> matrix;

	/**
	 * Creates all diffusible objects from file, then it creates and populates a new instance of {@code DiffusionLattice} with given dimension.
	 *
	 * @param max         The xy dimension of the lattice (x=y).
	 * @param dv          Voxel size
	 * @param diffusibles A list with all the diffusible substances to be simulated
	 * @param cells       the list of cells to be added to the lattice
	 */
	public DiffusionLattice2D(int max, double dv, List<Diffusible> diffusibles, List<? extends Cell> cells) {
		super(max, dv, diffusibles, cells);
		if (!cells.stream().allMatch(cell -> cell instanceof Cell2D))
			throw new IllegalArgumentException("All elements in 'cells' need to be Cell2D");
	}

	@Override
	public void updateCells(List<? extends Cell> cellList) {
		if (!cellList.stream().allMatch(cell -> cell instanceof Cell2D))
			throw new IllegalArgumentException("All elements in 'cells' need to be Cell2D");
		super.updateCells(cellList);
	}

	@Override
	protected GrowableMatrix<Voxel> createMatrix(ElementProvider<Voxel> voxelProvider, int max) {
		matrix = new ArrayMatrix2D<>(voxelProvider, max);
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

	private Position2D cellToPosition(Cell cell) throws IllegalArgumentException {
		return matrix.getScope().pointToPosition((Point2D) cell.getLocation(), getDv());
	}

	@Override
	protected Voxel getVoxelAt(int... indexes) throws IllegalArgumentException {
		if (indexes.length != 2)
			throw new IllegalArgumentException("This method must receive two indexes: i and j coordinates");
		return matrix.get(indexes[0], indexes[1]);
	}



	@Override
	protected double computeNeighboursTerm(Diffusible diffusible, double sn_ij, int... indexes) {
		int i = indexes[0];
		int j = indexes[1];

		double sn_ip1j = matrix.get(i + 1, j).getSubstances().get(diffusible); //sn at i+1, j
		double sn_im1j = matrix.get(i - 1, j).getSubstances().get(diffusible);
		double sn_ijp1 = matrix.get(i, j + 1).getSubstances().get(diffusible);
		double sn_ijm1 = matrix.get(i, j - 1).getSubstances().get(diffusible);
		return -4 * sn_ij + sn_ip1j + sn_im1j + sn_ijp1 + sn_ijm1;
	}

	@Override
	protected GrowableMatrix<Voxel> computeStagingMatrix(ElementProvider<Voxel> voxelProvider) {
		//Changes for next time point are stored in this matrix, then moved all at once to the main matrix.
		Matrix2D<Voxel> stagedChanges = new ArrayMatrix2D<>(voxelProvider, matrix.getScope().getMax());
		for (Position2D position2D : matrix.getScope()) { // loops all voxels
			Voxel currentVoxel = matrix.get(position2D);
			var concentrationsNp1 =  computeConcentrationsNp1(currentVoxel,
					position2D.isAtBoundary(), position2D.getI(), position2D.getJ());
			//replaces the concentration at n with concentration at n+1 in the stagedChangesMatrix
			stagedChanges.get(position2D).getSubstances().replaceAll((diffusible, oldConcentration) -> concentrationsNp1.get(diffusible));
		}
		return stagedChanges;
	}

	@Override
	public Map<String, Map<Diffusible, Double>> getConcentrationsPerVoxel(){
		Map<String, Map<Diffusible, Double>> map = new HashMap<>();
		for (Position2D position2D : matrix.getScope()) {
			map.put(position2D.toCSV(), matrix.get(position2D).getSubstances());
		}
		return map;
	}

	@Override
	public int getSize() {
		return matrix.getScope().getMax();
	}
}
