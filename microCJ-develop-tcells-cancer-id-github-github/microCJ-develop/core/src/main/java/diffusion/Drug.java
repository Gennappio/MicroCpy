/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package diffusion;

/**
 * Class that represent drugs: external substances, not produced by cells but injected manually, that have a temporary effect on an input node.
 * @author Pedro Victori
 */
class Drug extends DiffusibleBase{
	private int startTime;
	private int endTime;
	private double doseConcentration;

	public Drug(String name, String inputNode, Double initialConcentration, Double diffusionCoefficient,
	            Double threshold, Double defaultConsumption, int startTime, int endTime, double doseConcentration) {
		super(name, inputNode, initialConcentration, diffusionCoefficient, threshold, defaultConsumption);
		this.startTime = startTime;
		this.endTime = endTime;
		this.doseConcentration = doseConcentration;
	}

	Drug(Diffusible diffusible, int startTime, int endTime, double doseConcentration) {
		super(diffusible);
		this.startTime = startTime;
		this.endTime = endTime;
		this.doseConcentration = doseConcentration;
	}

	public int getStartTime() {
		return startTime;
	}

	public int getEndTime() {
		return endTime;
	}

	public double getDoseConcentration() {
		return doseConcentration;
	}
}
