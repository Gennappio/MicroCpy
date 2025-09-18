package diffusion.utils.twoDim;

import diffusion.utils.ElementProvider;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

public class ArrayMatrix2D<E> implements Matrix2D<E> {
	private List<List<E>> matrix;
	private Scope2D scope;

	/**
	 * Creates a populated instance of ArrayMatrix3D.
	 * The list of elements needs to be of the exact size required to fill a Matrix of dimensions xy where x = y.
	 * In other words, its square root must be an integer.
	 *
	 * @param elements the list of elements that will be used to populate the Matrix
	 */
	public ArrayMatrix2D(List<E> elements) {
		double root = Math.sqrt(elements.size());
		int scopeSize;
		if (root == Math.floor(root)) { //checks if the cube root is an integer and therefore the list has the adequate number of elements
			scopeSize = (int) root;
		} else throw new IllegalArgumentException("Invalid list size");
		scope = new Scope2D(scopeSize);
		matrix = new ArrayList<>(scopeSize);
		Iterator<E> it = elements.iterator();
		for (int i = 0; i < scopeSize; i++) {
			List<E> arrayJ = new ArrayList<>(scopeSize);
			for (int j = 0; j < scopeSize; j++) {
				arrayJ.add(it.next());
			}
			matrix.add(arrayJ);
		}
	}

	/**
	 * Creates a populated instance of ArrayMatrix2D with a give maximum size
	 * An {@code ElementProvider<E>} object is used to supply the required elements.
	 *
	 * @param provider an {@code ElementProvider<E>} able to supply the required number of elements.
	 * @param max      the maximum size
	 */
	public ArrayMatrix2D(ElementProvider<E> provider, int max) {
		this.scope = new Scope2D(max);
		matrix = new ArrayList<>(max);
		for (int i = 0; i < max; i++) {
			List<E> arrayJ = new ArrayList<>(max);
			for (int j = 0; j < max; j++) {
				arrayJ.add(provider.buildElement());
			}
			matrix.add(arrayJ);
		}
	}

	@Override
	public void grow(int growth, ElementProvider<E> elementProvider) {
		//create a new matrix filled with new elements
		ArrayMatrix2D<E> newMatrix = new ArrayMatrix2D<>(elementProvider, getScope().getMax() + growth);

		for (Position2D position2D : newMatrix.scope) {
			/*check if this position is inside the original matrix, therefore it has to be replaced with an old
			element from the original matrix. Otherwise, do nothing, since a new element was already generated
			in the previous step.*/
			if (position2D.shortestToBoundary() >= growth) {
				newMatrix.set(position2D, get(position2D));
			}
		}
		matrix = newMatrix.matrix;
		scope = newMatrix.scope;
	}

	@Override
	public E get(Position2D pos) {
		return get(pos.getI(), pos.getJ());
	}

	@Override
	public E get(int i, int j) {
		return matrix.get(i).get(j);
	}

	@Override
	public E set(Position2D pos, E element) {
		return set(pos.getI(), pos.getJ(), element);
	}

	@Override
	public E set(int i, int j, E element) {
		return matrix.get(i).set(j, element);
	}

	@Override
	public Scope2D getScope() {
		return scope;
	}
}
