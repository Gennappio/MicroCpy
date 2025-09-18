/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package diffusion.utils.threeDim;

import java.util.Iterator;

/**
 * Interface that represents a 3D matrix of equal dimensions i,j,k; i = j = k.
 * Contains methods for retrieving and setting elements at specific coordinates.
 * Coordinates can make use of the utility class Position3D
 *
 * @param <E> The contained elements type.
 * @author Pedro Victori
 */
public interface Matrix3D<E> extends GrowableMatrix<E> {
	/**
	 * Returns the element at the specified position
	 *
	 * @param pos an instance of Position3D, holding the ijk index of the element
	 * @return the element at the specified position
	 */
	E get(Position3D pos);

	/**
	 * Returns the element at the specified position
	 * @param i the i coordinate
	 * @param j the j coordinate
	 * @param k the k coordinate
	 * @return the element at the specified position
	 */
	E get(int i, int j, int k);

	/**
	 * Replaces the element at the specified position in this list with the specified element (optional operation).
	 * @param pos index of the element to replace
	 * @param element the new element to insert
	 * @return the element previously at that position, or null if no element there
	 */
	E set(Position3D pos, E element);

	/**
	 * Replaces the element at the specified position in this list with the specified element (optional operation).
	 * @param i the i coordinate
	 * @param j the j coordinate
	 * @param k the k coordinate
	 * @param element the new element to insert
	 * @return the element previously at that position, or null if no element there
	 */
	E set(int i, int j, int k, E element);

	Scope getScope();

	/**
	 * Returns an {@code Iterator} that provides the elements of the matrix in a fixed order from 0,0,0 to d,d,d
	 * @return an  {@code Iterator}.
	 */
	@Override
	default Iterator<E> iterator(){
		return new Iterator<>() {
			final Iterator<Position3D> it = getScope().iterator();

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