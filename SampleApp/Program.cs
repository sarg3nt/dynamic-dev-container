using System;

namespace SampleApp
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Hello from .NET in the dev container!");
            Console.WriteLine($"Current time: {DateTime.Now}");
            Console.WriteLine($".NET Version: {Environment.Version}");
            
            if (args.Length > 0)
            {
                Console.WriteLine($"Arguments: {string.Join(", ", args)}");
            }
        }
    }
}
