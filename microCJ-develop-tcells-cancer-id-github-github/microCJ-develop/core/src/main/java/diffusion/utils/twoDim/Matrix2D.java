package diffusion.utils.twoDim;

import diffusion.utils.threeDim.GrowableMatrix;

import java.util.Iterator;

public interface Matrix2D<E> extends GrowableMatrix<E> {
	/**
	 * Returns the element at the specified position
	 *
	 * @param pos an instance of Position2D, holding the ij index of the element
	 * @return the element at the specified position
	 */
	E get(Position2D pos);

	/**
	 * Returns the element at the specified position
	 *
	 * @param i the i coordinate
	 * @param j the j coordinate
	 * @return the element at the specified position
	 */
	E get(int i, int j);

	/**
	 * Replaces the element at the specified position in this list with the specified element (optional operation).
	 *
	 * @param pos     index of the element to replace
	 * @param element the new element to insert
	 * @return the element previously at that position, or null if no element there
	 */
	E set(Position2D pos, E element);

	/**
	 * Replaces the element at the specified position in this list with the specified element (optional operation).
	 *
	 * @param i       the i coordinate
	 * @param j       the j coordinate
	 * @param element the new element to insert
	 * @return the element previously at that position, or null if no element there
	 */
	E set(int i, int j, E element);

	Scope2D getScope();

	/**
	 * Returns an {@code Iterator} that provides the elements of the matrix in a fixed order from 0,0,0 to d,d,d
	 *
	 * @return an  {@code Iterator}.
	 */
	@Override
	default Iterator<E> iterator() {
		return new Iterator<>() {
			final Iterator<Position2D> it = getScope().iterator();

			@Override
			public boolean hasNext() {
				return it.hasNext();
			}

			@Override
			public E next() {
				return get(it.next());
			}

			@Override
			public void remove() {
				throw new UnsupportedOperationException();
			}
		};
	}
}
