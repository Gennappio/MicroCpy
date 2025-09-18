package geom.twoDim;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 2D matrix that can contain empty spaces
 *
 * @param <E> the type of elements in the matrix
 */
public class EmptiableMatrix<E> {
	private final List<List<E>> matrix = new ArrayList<>();
	private final int maxRowIndex;
	private final int maxColIndex;

	public EmptiableMatrix(int maxRowIndex, int maxColIndex, E emptyValue) {
		this.maxRowIndex = maxRowIndex;
		this.maxColIndex = maxColIndex;
		for (int i = 0; i <= maxRowIndex; i++) {
			matrix.add(new ArrayList<>(Collections.nCopies(maxColIndex + 1, emptyValue)));
		}
	}

	public E get(int row, int col) {
		return matrix.get(row).get(col);
	}

	public void put(int row, int col, E element) {
		matrix.get(row).set(col, element);
	}

	public int getMaxRowIndex() {
		return maxRowIndex;
	}

	public int getMaxColIndex() {
		return maxColIndex;
	}
}
