/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package stats;

import core.World;

/**
 * Functional interface to be implemented with specific methods for taking different measures.
 * @author Pedro Victori
 */
@FunctionalInterface
interface MeasureTaker {
	/**
	 * Takes a measure from the specified world.
	 * @param world the world to take the measure from
	 * @param option a single option, which is not necessarily used in every implementation, and admits a null value.
	 * @return a measure instance with the result of the calculation.
	 */
	Measure take(World world, String option);
}
