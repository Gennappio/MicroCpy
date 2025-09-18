/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package diffusion;

/**
 * Class to represent factors, substances that are produced and consumed by cells. Factors are produced upon activation of an output node and consumed by input nodes.
 * @author Pedro Victori
 */
class Factor extends DiffusibleBase{
	private final String outputNode;
	private final double production;

	public Factor(String name, String inputNode, String outputNode, Double initialConcentration, Double diffusionCoefficient, Double threshold, Double defaultConsumption, Double defaultProduction) {
		super(name, inputNode, initialConcentration, diffusionCoefficient, threshold, defaultConsumption);
		this.outputNode = outputNode;
		this.production = defaultProduction;
	}

	Factor(Diffusible diffusible, String outputNode, Double defaultProduction) {
		super(diffusible);
		this.outputNode = outputNode;
		this.production = defaultProduction;
	}

	String getOutputNode() {
		return outputNode;
	}

	/**
	 * Returns the default production of this substance by each cell
	 *
	 * @return a Double representing the default production of this substance
	 */
	Double getDefaultProduction() {
		return production;
	}
}
