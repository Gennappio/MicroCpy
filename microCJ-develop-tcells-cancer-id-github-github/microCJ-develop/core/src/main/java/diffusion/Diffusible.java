/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

package diffusion;

public interface Diffusible {
	/**
	 * Returns the name of the diffusible substance
	 * @return a String with the name of the substance
	 */
	String getName();

	/**
	 * Returns the initial concentration in every voxel.
	 * @return a Double representing the initial concentration
	 */
	Double getInitialConcentration();

	/**
	 * Returns the diffusion coefficient in m^2/s.
	 * @return a Double representing the diffusion coefficient in m^2/s.
	 */
	Double getDiffusionCoefficient();

	/**
	 * Returns the minimum concentration for the Diffusible to be consumed by a cell.
	 * @return a Double representing the minimum concentration for the Diffusible to be consumed by a cell.
	 */
	Double getThreshold();

	/**
	 * Returns the default consumption of this substance by each cell
	 * @return a Double representing the default consumption of this substance
	 */
	Double getDefaultConsumption();

	/**
	 *  Returns the input node activated by this substance.
	 * @return a String containing the unique tag of the input node.
	 */
	String getInputNode();

	/**
	 * Returns the dt term of this substance, for diffusion equation
	 * @return a double representing the dt term
	 */
	double getDt();

	/**
	 * Sets the dt term of this substance, for diffusion equation
	 * @param dt a double representing the dt term
	 */
	void setDt(Double dt);

	/**
	 * Wether this substance is oxygen or not. Specifically, its name must be oxygen for this method to return true: this method is equivalent to diffusible.getName().equals("oxygen");
	 * @return true if the substance is oxygen, false otherwise
	 */
	boolean isOxygen();
}
