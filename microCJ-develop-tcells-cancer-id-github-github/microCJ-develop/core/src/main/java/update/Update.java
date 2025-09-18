/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package update;

import java.util.Objects;

/**
 * Class for holding an update that will form part of a queue, and that is made of an UpdateFlag and an Updatable to which the UpdateFlag refers to
 *This class implements Comparable in order to sort different updates by priority. The comparison is actually made between the UpdateFlags.
 *Therefore, <strong>this class has a natural order that is inconsistent with equals.</strong>
 * @param <F> The UpdateFlag, used by compareTo().
 * @param <T> An Updatable, the target for the Update.
 * @author Pedro Victori
 */

public class Update <F extends UpdateFlag, T extends Updatable> implements Comparable<Update<F, T>>{
	private final F flag;
	private final T updatable;

	public Update(F flag, T updatable) {
		this.flag = flag;
		this.updatable = updatable;
	}

	public F getFlag() {
		return flag;
	}

	public T getUpdatable() {
		return updatable;
	}

	@Override
	public boolean equals(Object o) {
		if (this == o) return true;
		if (!(o instanceof Update)) return false;
		Update<?, ?> update = (Update<?, ?>) o;
		return Objects.equals(getFlag(), update.getFlag()) &&
				Objects.equals(getUpdatable(), update.getUpdatable());
	}

	@Override
	public int hashCode() {
		return Objects.hash(getFlag(), getUpdatable());
	}

	@Override
	public int compareTo(Update<F, T> o) {
		return flag.compareTo(o.getFlag());
	}
}
